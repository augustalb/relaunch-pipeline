"""Daily short report: new leads, sent, replies, bounces, costs. CLI + optional e-mail via Resend."""

from __future__ import annotations

from datetime import timedelta

import httpx
from sqlalchemy import func, select

from .config import get_settings
from .costs import costs_since
from .db import Lead, LeadStatus, session_scope, utcnow
from .log import get_logger

log = get_logger("report")


def build_report(days: int = 1) -> dict:
    since = utcnow() - timedelta(days=days)
    with session_scope() as session:
        def count(*conds) -> int:
            return session.scalar(select(func.count(Lead.id)).where(*conds)) or 0

        data = {
            "since": since.isoformat(timespec="minutes"),
            "new_leads": count(Lead.created_at >= since),
            "qualified": count(Lead.scored_at >= since, Lead.score >= get_settings().SCORE_THRESHOLD),
            "pending_review": count(Lead.status == LeadStatus.PENDING_REVIEW.value),
            "queued": count(Lead.status == LeadStatus.QUEUED.value),
            "sent": count(Lead.sent_at >= since),
            "replied": count(Lead.replied_at >= since),
            "bounced": count(Lead.status == LeadStatus.BOUNCED.value, Lead.updated_at >= since),
            "unsubscribed": count(Lead.status == LeadStatus.UNSUBSCRIBED.value, Lead.updated_at >= since),
            "won_total": count(Lead.status == LeadStatus.WON.value),
            "by_status": {st: n for st, n in session.execute(select(Lead.status, func.count(Lead.id)).group_by(Lead.status)).all()},
            "costs": costs_since(days),
        }
    data["costs_total_eur"] = round(sum(v["eur"] for v in data["costs"].values()), 4)
    return data


def format_report(data: dict) -> str:
    lines = [
        f"Kurzbericht seit {data['since']}",
        f"  Neue Leads:        {data['new_leads']}",
        f"  Qualifiziert:      {data['qualified']}",
        f"  Im Review:         {data['pending_review']}",
        f"  In Warteschlange:  {data['queued']}",
        f"  Versendet:         {data['sent']}",
        f"  Antworten:         {data['replied']}",
        f"  Bounces:           {data['bounced']}",
        f"  Abmeldungen:       {data['unsubscribed']}",
        f"  Gewonnen (gesamt): {data['won_total']}",
        f"  Kosten:            {data['costs_total_eur']:.2f} € " + ", ".join(f"{k}: {v['eur']:.2f} € ({v['requests']} Req.)" for k, v in data["costs"].items()),
        "  Status gesamt:     " + ", ".join(f"{k}={v}" for k, v in sorted(data["by_status"].items())),
    ]
    return "\n".join(lines)


def send_report_email(text: str) -> bool:
    s = get_settings()
    if not (s.RESEND_API_KEY and s.REPORT_EMAIL_TO and s.REPORT_EMAIL_FROM):
        return False
    if s.REPORT_EMAIL_FROM.lower() == s.REPLY_TO_EMAIL.lower():
        log.error("REPORT_EMAIL_FROM must not be the reply address – report not sent")
        return False
    try:
        r = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {s.RESEND_API_KEY}"},
            json={"from": s.REPORT_EMAIL_FROM, "to": [s.REPORT_EMAIL_TO], "subject": "Pipeline-Kurzbericht", "text": text},
            timeout=20,
        )
        return r.status_code < 300
    except httpx.HTTPError as e:
        log.warning("report mail failed", err=str(e))
        return False
