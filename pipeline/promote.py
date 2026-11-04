"""`pipeline promote <lead>` – turn a preview into the customer's production site."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .config import PROJECT_ROOT, get_settings
from .db import Lead, LeadStatus, session_scope
from .industry import load_industry
from .log import get_logger
from .services import cloudflare
from .stages.preview import build_site, preview_file, previews_dir, sync_industry_assets
from .util import slugify

log = get_logger("promote")


def customers_dir() -> Path:
    d = PROJECT_ROOT / "customers"
    d.mkdir(exist_ok=True)
    return d


def dns_instructions(project: str, domain: str) -> str:
    pages_host = f"{project}.pages.dev"
    return f"""
DNS-Anleitung für {domain}
==========================

Die Website läuft als eigenes Cloudflare-Pages-Projekt „{project}“ ({pages_host}).
Es werden ausschließlich Einträge für die Website gesetzt. MX-Einträge (E-Mail) werden NICHT angefasst.

Variante A – Domain bleibt beim bisherigen Anbieter (z. B. IONOS, Strato, 1&1):
  1. Im DNS der Domain anlegen/ändern:
       www    CNAME   {pages_host}
  2. Für die nackte Domain ({domain} ohne www):
       Wenn der Anbieter CNAME/ALIAS auf der Root-Domain erlaubt:  @  ALIAS/CNAME  {pages_host}
       Sonst: Weiterleitung {domain} -> https://www.{domain} beim Anbieter einrichten.
  3. In Cloudflare Pages -> Projekt „{project}“ -> Custom domains: www.{domain} (und ggf. {domain}) hinzufügen.
     Cloudflare stellt das SSL-Zertifikat automatisch aus (dauert bis zu 24 h).

Variante B – Domain zu Cloudflare umziehen (empfohlen, kostenlos):
  1. Cloudflare -> „Add a site“ -> {domain} -> Free-Plan. Cloudflare importiert vorhandene Einträge
     (inklusive MX!). Alle MX-/TXT-Einträge für E-Mail unverändert lassen.
  2. Nameserver beim bisherigen Anbieter auf die zwei Cloudflare-Nameserver ändern.
  3. Cloudflare Pages -> Projekt „{project}“ -> Custom domains: {domain} und www.{domain}.
     Cloudflare setzt die CNAME-Einträge selbst.

Prüfen: https://www.{domain} aufrufen, Schloss-Symbol im Browser, Impressum-Link funktioniert.
Niemals ändern: MX, SPF/DKIM/DMARC-TXT, autodiscover/imap/smtp-Einträge des Kunden.
"""


def promote(lead_ref: str, customer_domain: str | None = None, deploy: bool = True) -> dict:
    s = get_settings()
    with session_scope() as session:
        lead = session.get(Lead, int(lead_ref)) if lead_ref.isdigit() else session.query(Lead).filter(Lead.preview_path == lead_ref).one_or_none()
        if lead is None:
            raise SystemExit(f"Lead {lead_ref!r} nicht gefunden")
        if not lead.generated:
            raise SystemExit("Lead hat noch keine generierten Inhalte")
        industry = load_industry(lead.industry)
        name = slugify(lead.display_name, 40)
        project = f"site-{name}"
        cdir = customers_dir() / name
        cdir.mkdir(parents=True, exist_ok=True)
        data = preview_file(lead, industry, mode="production")
        data["meta"]["slug"] = name
        data["meta"]["custom_domain"] = customer_domain
        site_json = cdir / "site.json"
        if site_json.exists():
            data = json.loads(site_json.read_text(encoding="utf-8"))  # edits made by hand win
            data["meta"]["mode"] = "production"
        site_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        if lead.status_enum in (LeadStatus.REPLIED,):
            lead.transition(LeadStatus.WON, "promoted", session)
        lead_id = lead.id
    # Build: temporarily place the customer's JSON as the only preview, with PROMOTE_SLUG so it renders at "/"
    pdir = previews_dir()
    backup = [p for p in pdir.glob("*.json")]
    tmp = PROJECT_ROOT / "customers" / ".build-backup"
    tmp.mkdir(exist_ok=True)
    for p in backup:
        shutil.move(str(p), tmp / p.name)
    try:
        (pdir / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        sync_industry_assets()
        dist = cdir / "dist"
        built = build_site({"PROMOTE_SLUG": name, "SITE_URL": f"https://{customer_domain}" if customer_domain else f"https://{project}.pages.dev"}, out_dir=dist)
        if built:
            # production sites are indexable: drop the preview robots/header files
            for f in ("robots.txt", "_headers"):
                p = dist / f
                if p.exists():
                    p.unlink()
            (dist / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
    finally:
        (pdir / f"{name}.json").unlink(missing_ok=True)
        for p in tmp.glob("*.json"):
            shutil.move(str(p), pdir / p.name)
    deployed = False
    if built and deploy:
        cloudflare.ensure_project(project)
        deployed = cloudflare.deploy(built, project=project)
    instructions = dns_instructions(project, customer_domain or "kunden-domain.de")
    (cdir / "DNS-ANLEITUNG.md").write_text(instructions, encoding="utf-8")
    print(instructions)
    log.info("promoted", lead=lead_id, project=project, deployed=deployed, dir=str(cdir))
    return {"lead": lead_id, "project": project, "dir": str(cdir), "deployed": deployed, "site_json": str(site_json)}
