"""Stage 9 – Queue approved leads and hand them to the Sender within limits and send window."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from ..config import get_settings
from ..db import Lead, LeadStatus, SendCounter, leads_in_status, session_scope, utcnow
from ..emails import render_sequence
from ..industry import load_industry
from ..log import get_logger
from ..services import blocklist as bl
from ..services.sender import Campaign, OutboundMessage, Recipient, Sender, make_sender

log = get_logger("sending")


def now_berlin(now: datetime | None = None) -> datetime:
    tz = ZoneInfo(get_settings().TIMEZONE)
    return (now or utcnow()).astimezone(tz)


def in_send_window(now: datetime | None = None) -> bool:
    s = get_settings()
    t = now_berlin(now)
    if s.SEND_WEEKDAYS_ONLY and t.weekday() >= 5:
        return False
    return s.SEND_WINDOW_START_HOUR <= t.hour < s.SEND_WINDOW_END_HOUR


def daily_limit(first_send_day: datetime | None, today: datetime | None = None) -> int:
    """Ramp: start limit, +RAMP_PER_WEEK every 7 days since the first send, capped at max."""
    s = get_settings()
    if first_send_day is None:
        return s.DAILY_SEND_LIMIT_START
    today = today or utcnow()
    weeks = max(0, (today.date() - first_send_day.date()).days // 7)
    return min(s.DAILY_SEND_LIMIT_MAX, s.DAILY_SEND_LIMIT_START + weeks * s.DAILY_SEND_LIMIT_RAMP_PER_WEEK)


def queue_approved(limit: int | None = None) -> int:
    industry = load_industry()
    n = 0
    with session_scope() as session:
        for lead in leads_in_status(session, LeadStatus.APPROVED, limit, industry.name):
            if not lead.email_body:
                emails = render_sequence(industry, lead)
                lead.email_subject, lead.email_body = emails[0].subject, emails[0].body
                lead.followup_1_body, lead.followup_2_body = emails[1].body, emails[2].body
            lead.transition(LeadStatus.QUEUED, None, session)
            n += 1
    return n


def send_queued(limit: int | None = None, sender: Sender | None = None, force_window: bool = False) -> dict:
    s = get_settings()
    industry = load_industry()
    sender = sender or make_sender()
    stats = {"sent": 0, "skipped_window": 0, "skipped_limit": 0, "blocked": 0, "unverified": 0, "errors": 0}
    if not force_window and not in_send_window():
        log.info("outside send window (Mo–Fr %d–%d Uhr %s) – nothing sent" % (s.SEND_WINDOW_START_HOUR, s.SEND_WINDOW_END_HOUR, s.TIMEZONE))
        stats["skipped_window"] = 1
        return stats
    today = now_berlin().strftime("%Y-%m-%d")
    with session_scope() as session:
        first = session.scalar(select(func.min(Lead.sent_at)))
        counter = session.get(SendCounter, today) or SendCounter(day=today, count=0)
        session.add(counter)
        cap = daily_limit(first)
        remaining = max(0, cap - counter.count)
        if limit:
            remaining = min(remaining, limit)
        ids = [l.id for l in leads_in_status(session, LeadStatus.QUEUED, remaining or None, industry.name)] if remaining else []
        if not remaining:
            stats["skipped_limit"] = 1
            log.info("daily limit reached", cap=cap, sent_today=counter.count)
    for lead_id in ids:
        with session_scope() as session:
            lead = session.get(Lead, lead_id)
            if bl.is_blocked(session, lead.email, lead.domain):
                lead.transition(LeadStatus.REJECTED, "auf Sperrliste", session)
                stats["blocked"] += 1
                continue
            if s.REQUIRE_VERIFIED_EMAIL and not lead.email_verified and sender.name != "dryrun":
                stats["unverified"] += 1
                log.info("skipping unverified address (REQUIRE_VERIFIED_EMAIL=true)", lead=lead_id, email=lead.email)
                continue
            first_name = last_name = ""
            if lead.owner_name:
                parts = lead.owner_name.split()
                first_name, last_name = parts[0], " ".join(parts[1:])
            campaign = Campaign(
                recipient=Recipient(email=lead.email, company=lead.display_name, first_name=first_name, last_name=last_name, website=lead.website or "", city=lead.city or "", lead_id=lead.id),
                messages=[
                    OutboundMessage(1, lead.email_subject or "", lead.email_body or "", 0),
                    OutboundMessage(2, "Re: " + (lead.email_subject or ""), lead.followup_1_body or "", s.FOLLOWUP_1_DAYS),
                    OutboundMessage(3, "Re: " + (lead.email_subject or ""), lead.followup_2_body or "", s.FOLLOWUP_2_DAYS),
                ],
                reply_to=s.REPLY_TO_EMAIL,
                variables={"preview_url": lead.preview_url or "", "anrede": lead.owner_salutation or "Guten Tag"},
            )
            result = sender.send(campaign)
            if not result.ok:
                stats["errors"] += 1
                log.error("send failed", lead=lead_id, err=result.error)
                continue
            lead.sent_at = utcnow()
            lead.sender_ref = result.reference
            lead.transition(LeadStatus.SENT, sender.name, session)
            counter = session.get(SendCounter, today)
            counter.count += 1
            stats["sent"] += 1
    log.info("sending done", **stats)
    return stats


def run(limit: int | None = None, sender: Sender | None = None, force_window: bool = False) -> dict:
    queued = queue_approved(limit)
    out = send_queued(limit, sender, force_window)
    out["queued"] = queued
    return out


_ = timedelta
