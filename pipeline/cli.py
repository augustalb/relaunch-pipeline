"""Single CLI entry point: `pipeline <command>`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.table import Table

from .config import get_settings
from .log import configure_logging

app = typer.Typer(help="Akquise-Pipeline für Website-Relaunches (Discovery → Scoring → Preview → E-Mail).", no_args_is_help=True)


@app.callback()
def _init(log_level: str = typer.Option(None, help="DEBUG/INFO/WARNING"), json_logs: bool = typer.Option(False, "--json-logs")):
    s = get_settings()
    configure_logging(log_level or s.LOG_LEVEL, json_logs or s.LOG_JSON)


@app.command()
def run(
    stage: str = typer.Option("all", help="all | redo_review | " + " | ".join(__import__("pipeline.runner", fromlist=["STAGES"]).STAGES)),
    limit: Optional[int] = typer.Option(None, help="max. Leads pro Stufe"),
    no_deploy: bool = typer.Option(False, "--no-deploy", help="Preview nur lokal bauen"),
    force_window: bool = typer.Option(False, "--force-window", help="Versandfenster ignorieren (nur Dry-Run/Tests)"),
):
    """Pipeline-Stufen ausführen (idempotent, jederzeit neu startbar)."""
    from .runner import run_all

    summary = run_all(stage, limit, deploy=not no_deploy, force_window=force_window)
    rprint(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


@app.command()
def review(host: str = typer.Option(None), port: int = typer.Option(None), open_browser: bool = typer.Option(True)):
    """Lokale Review-Oberfläche starten (Vorher/Nachher, Befunde, Mail, Freigabe)."""
    import uvicorn

    s = get_settings()
    host, port = host or s.REVIEW_HOST, port or s.REVIEW_PORT
    rprint(f"[bold]Review-UI:[/bold] http://{host}:{port}")
    if open_browser:
        import threading
        import webbrowser

        threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run("pipeline.review.app:app", host=host, port=port, log_level="warning")


@app.command()
def report(days: int = typer.Option(1), email: bool = typer.Option(False, help="zusätzlich per E-Mail (Resend) an REPORT_EMAIL_TO")):
    """Täglicher Kurzbericht."""
    from .report import build_report, format_report, send_report_email

    data = build_report(days)
    text = format_report(data)
    print(text)
    if email:
        rprint("[green]E-Mail gesendet[/green]" if send_report_email(text) else "[yellow]E-Mail nicht gesendet (RESEND_API_KEY/REPORT_EMAIL_* fehlen?)[/yellow]")


@app.command()
def promote(lead: str = typer.Argument(..., help="Lead-ID oder Preview-Slug"), domain: Optional[str] = typer.Option(None, help="Kundendomain, z. B. fahrschule-mueller.de"), no_deploy: bool = typer.Option(False, "--no-deploy")):
    """Preview in ein eigenes Produktionsprojekt (Cloudflare Pages) überführen + DNS-Anleitung."""
    from .promote import promote as _promote

    rprint(_promote(lead, domain, deploy=not no_deploy))


@app.command()
def demo(reset: bool = typer.Option(True, help="Demo-Datenbank vorher leeren"), skip_screenshots: bool = typer.Option(False), skip_build: bool = typer.Option(False), limit: Optional[int] = typer.Option(None)):
    """Kompletter Offline-Durchlauf mit den lokalen Fixtures (keine Keys nötig)."""
    from .demo import run_demo

    summary = run_demo(reset=reset, screenshots=not skip_screenshots, build=not skip_build, limit=limit)
    rprint(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


@app.command()
def leads(status: Optional[str] = typer.Option(None), limit: int = typer.Option(50)):
    """Leads anzeigen."""
    from sqlalchemy import select

    from .db import Lead, session_scope

    with session_scope() as s:
        stmt = select(Lead).order_by(Lead.id.desc()).limit(limit)
        if status:
            stmt = stmt.where(Lead.status == status)
        rows = list(s.scalars(stmt))
    t = Table("ID", "Status", "Firma", "Stadt", "Score", "E-Mail", "Preview")
    for l in rows:
        t.add_row(str(l.id), l.status, l.display_name[:32], l.city or "", str(l.score or ""), l.email or "", l.preview_url or "")
    rprint(t)


@app.command()
def approve(lead_ids: list[int] = typer.Argument(...)):
    """Leads per CLI freigeben (Alternative zur Web-Oberfläche)."""
    from .review.actions import approve as _approve

    for lid in lead_ids:
        rprint(_approve(lid))


@app.command()
def reject(lead_ids: list[int] = typer.Argument(...), reason: str = typer.Option("manuell abgelehnt")):
    from .review.actions import reject as _reject

    for lid in lead_ids:
        rprint(_reject(lid, reason))


@app.command()
def block(values: list[str] = typer.Argument(..., help="E-Mail-Adressen oder Domains")):
    """Einträge zur globalen Sperrliste hinzufügen."""
    from .db import session_scope
    from .services import blocklist as bl

    with session_scope() as s:
        for v in values:
            rprint(f"{v}: {'hinzugefügt' if bl.add(s, v, 'cli') else 'bereits vorhanden'}")


@app.command()
def doctor(live: bool = typer.Option(False, "--live", help="Jeden Dienst einmal kostenlos abfragen; Exit-Code 1 bei Fehlern")):
    """Zeigt, welche Keys/Tools vorhanden sind und welche Stufen degradiert laufen."""
    import shutil

    s = get_settings()
    checks = [
        ("Datenbank", s.database_url.split("@")[-1] if "@" in s.database_url else s.database_url),
        ("GOOGLE_PLACES_API_KEY", "ok" if s.GOOGLE_PLACES_API_KEY else "fehlt → Discovery übersprungen"),
        ("PAGESPEED_API_KEY", "ok" if s.PAGESPEED_API_KEY else "fehlt → PSI ohne Key (geringe Quote)"),
        ("ANTHROPIC_API_KEY", "ok" if s.ANTHROPIC_API_KEY else "fehlt → regelbasierte Generierung"),
        ("CLOUDFLARE_API_TOKEN", "ok" if s.CLOUDFLARE_API_TOKEN else "fehlt → kein Deploy, nur lokaler Build"),
        ("INSTANTLY_API_KEY", "ok" if s.INSTANTLY_API_KEY else "fehlt → DryRunSender (outbox/)"),
        ("MILLIONVERIFIER_API_KEY", "ok" if s.MILLIONVERIFIER_API_KEY else "fehlt → nur Syntax/MX-Prüfung"),
        ("node/npm", shutil.which("npm") or "fehlt → kein Preview-Build"),
        ("Playwright", _playwright_status()),
        ("SENDER_BACKEND", s.SENDER_BACKEND),
        ("AUTO_APPROVE", str(s.AUTO_APPROVE)),
        ("Branche", f"{s.INDUSTRY} ({s.industry_dir})"),
    ]
    t = Table("Prüfung", "Status")
    for k, v in checks:
        t.add_row(k, str(v))
    rprint(t)

    if live:
        from .livecheck import run_live_checks

        results = run_live_checks()
        lt = Table("Live-Prüfung", "Status", "Details")
        for r in results:
            lt.add_row(r.name, r.status, r.detail)
        rprint(lt)
        if any(r.failed for r in results):
            raise typer.Exit(code=1)


def _playwright_status() -> str:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            b = p.chromium.launch(args=["--no-sandbox"])
            b.close()
        return "ok"
    except Exception as e:
        return f"nicht nutzbar ({str(e)[:60]}…) → keine Screenshots"


if __name__ == "__main__":
    app()
