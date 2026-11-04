"""Review actions shared by the web UI and the CLI."""

from __future__ import annotations

from ..db import Lead, LeadStatus, session_scope, utcnow
from ..emails import render_sequence
from ..industry import load_industry


def _ensure_emails(lead: Lead) -> None:
    if not lead.email_body:
        emails = render_sequence(load_industry(lead.industry), lead)
        lead.email_subject, lead.email_body = emails[0].subject, emails[0].body
        lead.followup_1_body, lead.followup_2_body = emails[1].body, emails[2].body


def approve(lead_id: int, subject: str | None = None, body: str | None = None) -> str:
    with session_scope() as s:
        lead = s.get(Lead, lead_id)
        if lead is None:
            return f"{lead_id}: nicht gefunden"
        if lead.status_enum not in (LeadStatus.PENDING_REVIEW, LeadStatus.GENERATED):
            return f"{lead_id}: Status {lead.status}, keine Freigabe möglich"
        _ensure_emails(lead)
        if subject is not None:
            lead.email_subject = subject
        if body is not None:
            lead.email_body = body
        lead.approved_at = utcnow()
        lead.transition(LeadStatus.APPROVED, "review", s)
        return f"{lead_id}: freigegeben"


def reject(lead_id: int, reason: str = "abgelehnt") -> str:
    with session_scope() as s:
        lead = s.get(Lead, lead_id)
        if lead is None:
            return f"{lead_id}: nicht gefunden"
        if lead.status_enum not in (LeadStatus.PENDING_REVIEW, LeadStatus.APPROVED, LeadStatus.QUEUED):
            return f"{lead_id}: Status {lead.status}, keine Ablehnung möglich"
        lead.transition(LeadStatus.REJECTED, reason, s)
        return f"{lead_id}: abgelehnt"


def save_email(lead_id: int, subject: str, body: str) -> str:
    with session_scope() as s:
        lead = s.get(Lead, lead_id)
        if lead is None:
            return "nicht gefunden"
        lead.email_subject, lead.email_body = subject, body
        return "gespeichert"
