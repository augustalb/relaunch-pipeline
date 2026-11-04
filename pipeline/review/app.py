"""Lean local review UI (FastAPI + Jinja2). Lists leads in `pending_review` with before/after
screenshots, findings, validator warnings, the rendered e-mail and the preview link."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from ..config import PROJECT_ROOT, get_settings
from ..db import Lead, LeadStatus, session_scope
from ..emails import check_email, render_sequence
from ..industry import load_industry
from . import actions

app = FastAPI(title="Relaunch-Pipeline Review")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _leads(status: str) -> list[dict]:
    with session_scope() as s:
        rows = list(s.scalars(select(Lead).where(Lead.status == status).order_by(Lead.id)))
        out = []
        for l in rows:
            if not l.email_body:
                emails = render_sequence(load_industry(l.industry), l)
                l.email_subject, l.email_body = emails[0].subject, emails[0].body
                l.followup_1_body, l.followup_2_body = emails[1].body, emails[2].body
            out.append(
                {
                    "id": l.id,
                    "name": l.display_name,
                    "city": l.city,
                    "website": l.website,
                    "email": l.email,
                    "email_verification": l.email_verification,
                    "score": l.score,
                    "findings": l.findings or [],
                    "warnings": l.validator_warnings or [],
                    "email_warnings": check_email(l.email_body or ""),
                    "subject": l.email_subject,
                    "body": l.email_body,
                    "followup_1": l.followup_1_body,
                    "followup_2": l.followup_2_body,
                    "preview_url": l.preview_url,
                    "preview_path": l.preview_path,
                    "before": bool(l.screenshot_before and Path(l.screenshot_before).exists()),
                    "after": bool(l.screenshot_after and Path(l.screenshot_after).exists()),
                    "sections": list((l.generated or {}).keys()),
                    "salutation": l.owner_salutation or "Guten Tag",
                    "owner": l.owner_name,
                }
            )
        return out


@app.get("/", response_class=HTMLResponse)
def index(request: Request, status: str = LeadStatus.PENDING_REVIEW.value, msg: str = ""):
    s = get_settings()
    with session_scope() as sess:
        counts = {st: n for st, n in sess.execute(select(Lead.status, __import__("sqlalchemy").func.count(Lead.id)).group_by(Lead.status)).all()}
    local_preview = (s.SITE_DIR / "dist").exists()
    return templates.TemplateResponse(request, "index.html", {"leads": _leads(status), "status": status, "counts": counts, "msg": msg, "auto_approve": s.AUTO_APPROVE, "local_preview": local_preview, "statuses": [x.value for x in LeadStatus]})


@app.post("/approve/{lead_id}")
def approve(lead_id: int, subject: str = Form(None), body: str = Form(None)):
    return RedirectResponse(f"/?msg={actions.approve(lead_id, subject, body)}", status_code=303)


@app.post("/reject/{lead_id}")
def reject(lead_id: int, reason: str = Form("abgelehnt")):
    return RedirectResponse(f"/?msg={actions.reject(lead_id, reason)}", status_code=303)


@app.post("/save/{lead_id}")
def save(lead_id: int, subject: str = Form(...), body: str = Form(...)):
    return RedirectResponse(f"/?msg={lead_id}: {actions.save_email(lead_id, subject, body)}", status_code=303)


@app.post("/approve-all")
def approve_all(only_clean: bool = Form(True)):
    n = 0
    for l in _leads(LeadStatus.PENDING_REVIEW.value):
        if only_clean and (l["warnings"] or l["email_warnings"]):
            continue
        actions.approve(l["id"])
        n += 1
    return RedirectResponse(f"/?msg={n} Leads freigegeben", status_code=303)


@app.get("/shot/{lead_id}/{which}")
def shot(lead_id: int, which: str):
    with session_scope() as s:
        lead = s.get(Lead, lead_id)
        path = lead.screenshot_before if which == "before" else lead.screenshot_after
    if path and Path(path).exists():
        return FileResponse(path)
    return HTMLResponse("kein Screenshot", status_code=404)


@app.get("/preview/{slug}/{path:path}")
def local_preview(slug: str, path: str = ""):
    """Serve the locally built preview (site/dist) when nothing is deployed yet."""
    base = get_settings().SITE_DIR / "dist"
    target = base / slug / (path or "index.html")
    if target.is_dir():
        target = target / "index.html"
    if target.exists():
        return FileResponse(target)
    return HTMLResponse("nicht gebaut – `pipeline run --stage preview --no-deploy`", status_code=404)


_ = PROJECT_ROOT
