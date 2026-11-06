"""Static review report: one HTML page with everything needed to approve or reject leads.

Written to `review/index.html` (+ `review/img/`) and uploaded as a GitHub Actions artifact, so the
operator can review on any device without running the local review UI. Approve/reject happens by
starting the workflow with the lead IDs (inputs `approve` / `reject`).
"""

from __future__ import annotations

import html
import shutil
from pathlib import Path

from sqlalchemy import select

from ..config import PROJECT_ROOT, get_settings
from ..db import Lead, LeadStatus, session_scope
from ..emails import check_email, render_sequence
from ..industry import load_industry
from ..log import get_logger

log = get_logger("review-export")

CSS = """
:root{--ink:#14202b;--muted:#5b6770;--line:#e2ded5;--paper:#f6f4ef;--card:#fff;--teal:#0f7a6c;--warn:#b5561a;--bad:#b23b14}
*{box-sizing:border-box}body{margin:0;font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--paper)}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}h1{font-size:1.8rem;margin:0 0 4px}.lead-intro{color:var(--muted);margin:0 0 24px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;margin:0 0 24px}
.head{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:baseline;justify-content:space-between}
.id{font-weight:800;background:var(--ink);color:#fff;border-radius:999px;padding:4px 12px;font-size:.9rem}
h2{font-size:1.35rem;margin:0}.meta{color:var(--muted);font-size:.92rem;margin:4px 0 12px}.meta a{color:var(--teal)}
.shots{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0}.shots figure{margin:0}.shots img{width:100%;border:1px solid var(--line);border-radius:12px}
.shots figcaption{font-weight:700;font-size:.8rem;letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px}
h3{font-size:1rem;margin:18px 0 6px}ul{margin:0;padding-left:1.2em}.warn li{color:var(--warn)}.ok{color:var(--teal);font-weight:600}
pre{white-space:pre-wrap;background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:12px;font:14px/1.5 ui-monospace,Menlo,monospace;margin:0}
details{margin:8px 0}summary{cursor:pointer;font-weight:600}.how{background:#e2f4ef;border-radius:12px;padding:14px 16px;margin:0 0 24px}
code{background:var(--paper);padding:1px 6px;border-radius:6px}
@media(max-width:640px){.shots{grid-template-columns:1fr}}
"""


def _e(x) -> str:
    return html.escape(str(x or ""))


def _list(items, cls: str = "") -> str:
    items = [i for i in (items or []) if i]
    if not items:
        return '<p class="ok">keine</p>'
    return f'<ul class="{cls}">' + "".join(f"<li>{_e(i)}</li>" for i in items) + "</ul>"


def export(out_dir: Path | None = None) -> dict:
    s = get_settings()
    out = out_dir or PROJECT_ROOT / "review"
    if out.exists():
        shutil.rmtree(out)
    (out / "img").mkdir(parents=True)
    cards, ids = [], []
    with session_scope() as session:
        leads = list(session.scalars(select(Lead).where(Lead.status == LeadStatus.PENDING_REVIEW.value).order_by(Lead.id)))
        for lead in leads:
            mails = render_sequence(load_industry(lead.industry), lead)
            shots = []
            for kind, path in (("Vorher", lead.screenshot_before), ("Nachher (Entwurf)", lead.screenshot_after)):
                if path and Path(path).exists():
                    name = f"{lead.id}-{'before' if kind == 'Vorher' else 'after'}.png"
                    shutil.copy(path, out / "img" / name)
                    shots.append(f'<figure><figcaption>{kind}</figcaption><img src="img/{name}" alt="{kind}" loading="lazy"></figure>')
            details = lead.score_details or {}
            visual = details.get("visual") or {}
            pages_url = f"https://{s.CLOUDFLARE_PAGES_PROJECT}.pages.dev/{lead.preview_path}/" if lead.preview_path else ""
            mail_html = "".join(
                f"<details{' open' if i == 0 else ''}><summary>Mail {i + 1}: {_e(m.subject)}</summary><pre>{_e(m.body)}</pre></details>"
                for i, m in enumerate(mails)
            )
            mail_warnings = check_email(mails[0].body)
            cards.append(f"""
<section class="card">
  <div class="head"><h2>{_e(lead.display_name)}</h2><span class="id">ID {lead.id}</span></div>
  <p class="meta">{_e(lead.city)} · <a href="{_e(lead.website)}">{_e(lead.website)}</a> · Score {lead.score} ·
     Empfänger: {_e(lead.email)} ({_e(lead.email_verification)}) · Anrede: {_e(lead.owner_salutation or 'Guten Tag')}<br>
     Entwurf: <a href="{_e(pages_url)}">{_e(pages_url)}</a></p>
  <div class="shots">{''.join(shots) or '<p>Keine Screenshots vorhanden.</p>'}</div>
  <h3>Befunde für die Mail</h3>{_list(lead.findings)}
  <h3>Einschätzung der KI (nur für die Auswahl, nicht in der Mail)</h3>
  <p>Veraltet {visual.get('outdated', '–')}/10 · Handy-Bedienbarkeit {visual.get('mobile_usability', '–')}/10</p>{_list(visual.get('reasons'))}
  <h3>Warnungen der Faktenprüfung</h3>{_list(lead.validator_warnings, 'warn')}
  <h3>Warnungen zur Mail</h3>{_list(mail_warnings, 'warn')}
  <h3>Mails</h3>{mail_html}
</section>""")
            ids.append(lead.id)
    page = f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Review – Relaunch-Pipeline</title><style>{CSS}</style></head><body><main>
<h1>Entwürfe zur Freigabe</h1><p class="lead-intro">{len(cards)} Fahrschulen warten auf Ihre Entscheidung.</p>
<div class="how"><strong>So geben Sie frei:</strong> GitHub → Actions → relaunch-pipeline → „Run workflow“.
Bei <code>approve</code> die IDs eintragen, die raus dürfen (z. B. <code>{', '.join(map(str, ids[:2])) or '12, 13'}</code>),
bei <code>reject</code> die abgelehnten. Stufe <code>sending</code> wählen. Solange <code>SENDER_BACKEND=dryrun</code> gilt, entstehen nur Probe-Mails.</div>
{''.join(cards) or '<p>Keine Entwürfe im Review.</p>'}
</main></body></html>"""
    (out / "index.html").write_text(page, encoding="utf-8")
    log.info("review report written", leads=len(cards), path=str(out / "index.html"))
    return {"leads": len(cards), "path": str(out / "index.html")}
