"""Stage 10 – Pull replies/bounces/unsubscribes from the sequencer, update statuses, maintain blocklist."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from ..db import Lead, LeadStatus, session_scope, utcnow
from ..log import get_logger
from ..services import blocklist as bl
from ..services.sender import InboundEvent, Sender, make_sender

log = get_logger("sync")

NEGATIVE_HINTS = ("kein interesse", "kein bedarf", "nicht interessiert", "keine weiteren", "nicht mehr", "bitte keine", "abmelden", "unsubscribe", "spam", "lassen sie", "unterlassen", "streichen sie")


def classify_reply(excerpt: str | None) -> str:
    t = (excerpt or "").lower()
    if any(h in t for h in NEGATIVE_HINTS):
        return "negative"
    return "neutral"


def apply_event(session, ev: InboundEvent) -> str | None:
    lead = session.scalar(select(Lead).where(Lead.email == ev.email.lower()).order_by(Lead.sent_at.desc()))
    if lead is None:
        return None
    status = lead.status_enum
    if ev.kind == "bounced" and status == LeadStatus.SENT:
        lead.transition(LeadStatus.BOUNCED, ev.excerpt, session)
        bl.add(session, ev.email, "bounce")
        return "bounced"
    if ev.kind == "unsubscribed" and status in (LeadStatus.SENT, LeadStatus.REPLIED, LeadStatus.QUEUED):
        lead.transition(LeadStatus.UNSUBSCRIBED, ev.excerpt, session)
        bl.block_contact(session, lead.email, lead.domain, "unsubscribe")
        return "unsubscribed"
    if ev.kind in ("replied", "interested") and status == LeadStatus.SENT:
        lead.replied_at = ev.at
        lead.last_reply_excerpt = ev.excerpt
        if classify_reply(ev.excerpt) == "negative":
            lead.transition(LeadStatus.REPLIED, ev.excerpt, session)
            lead.transition(LeadStatus.LOST, "ablehnende Antwort", session)
            bl.block_contact(session, lead.email, lead.domain, "negative reply")
            return "lost"
        lead.transition(LeadStatus.REPLIED, ev.excerpt, session)
        return "replied"
    if ev.kind == "not_interested" and status in (LeadStatus.SENT, LeadStatus.REPLIED):
        if status == LeadStatus.SENT:
            lead.transition(LeadStatus.REPLIED, "not interested (sequencer)", session)
        lead.transition(LeadStatus.LOST, "not interested (sequencer)", session)
        bl.block_contact(session, lead.email, lead.domain, "not interested")
        return "lost"
    return None


def run(sender: Sender | None = None, days: int = 14) -> dict:
    sender = sender or make_sender()
    stats: dict[str, int] = {"events": 0, "manual_blocklist": 0}
    with session_scope() as session:
        stats["manual_blocklist"] = bl.sync_manual_file(session)
        events = sender.sync(utcnow() - timedelta(days=days))
        for ev in events:
            stats["events"] += 1
            outcome = apply_event(session, ev)
            if outcome:
                stats[outcome] = stats.get(outcome, 0) + 1
    log.info("sync done", **stats)
    return stats
