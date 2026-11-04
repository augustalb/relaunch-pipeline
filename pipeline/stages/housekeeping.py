"""Expiry of previews (45 days without reply) and Places cache scrubbing (ToS)."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from ..config import get_settings
from ..db import Lead, LeadStatus, session_scope, utcnow
from ..log import get_logger

log = get_logger("housekeeping")


def expire_previews() -> int:
    """Leads that were sent/bounced/lost >= PREVIEW_EXPIRE_DAYS ago lose their preview."""
    s = get_settings()
    cutoff = utcnow() - timedelta(days=s.PREVIEW_EXPIRE_DAYS)
    n = 0
    with session_scope() as session:
        for lead in session.scalars(select(Lead).where(Lead.status.in_([LeadStatus.SENT.value, LeadStatus.BOUNCED.value, LeadStatus.LOST.value]), Lead.sent_at <= cutoff)):
            _remove_preview_file(lead)
            lead.transition(LeadStatus.EXPIRED, f"{s.PREVIEW_EXPIRE_DAYS} Tage ohne Antwort", session)
            n += 1
    if n:
        log.info("previews expired (re-deploy removes them)", n=n)
    return n


def _remove_preview_file(lead: Lead) -> None:
    s = get_settings()
    if lead.preview_path:
        f = s.SITE_DIR / "src" / "data" / "previews" / f"{lead.preview_path}.json"
        if f.exists():
            f.unlink()


def scrub_places_cache() -> int:
    """Google Maps Platform ToS: don't keep Places content (except place_id) beyond 30 days."""
    s = get_settings()
    cutoff = utcnow() - timedelta(days=s.PLACES_CACHE_DAYS)
    n = 0
    with session_scope() as session:
        for lead in session.scalars(select(Lead).where(Lead.places_cached_at <= cutoff)):
            lead.places_name = None
            lead.places_address = None
            lead.places_phone = None
            lead.places_rating = None
            lead.places_rating_count = None
            lead.places_cached_at = None
            n += 1
    if n:
        log.info("places cache scrubbed", n=n)
    return n


def run() -> dict:
    return {"expired": expire_previews(), "places_scrubbed": scrub_places_cache()}
