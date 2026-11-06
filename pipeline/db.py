"""Database layer (SQLAlchemy 2.0). SQLite locally, Postgres (Supabase) in production.

The same ORM code path is used for both, so the demo run exercises exactly
what runs in GitHub Actions.
"""

from __future__ import annotations

import enum
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from .config import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LeadStatus(str, enum.Enum):
    """The fixed status chain every lead walks through (see README)."""

    DISCOVERED = "discovered"
    SCORED = "scored"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"
    CONTACT_FOUND = "contact_found"
    NO_CONTACT = "no_contact"
    EXTRACTED = "extracted"
    GENERATED = "generated"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    QUEUED = "queued"
    SENT = "sent"
    REPLIED = "replied"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"
    WON = "won"
    LOST = "lost"
    EXPIRED = "expired"


# Transitions every stage is allowed to make. Enforced in Lead.transition().
ALLOWED_TRANSITIONS: dict[LeadStatus, set[LeadStatus]] = {
    LeadStatus.DISCOVERED: {LeadStatus.SCORED, LeadStatus.DISQUALIFIED},
    LeadStatus.SCORED: {LeadStatus.QUALIFIED, LeadStatus.DISQUALIFIED},
    LeadStatus.QUALIFIED: {LeadStatus.CONTACT_FOUND, LeadStatus.NO_CONTACT, LeadStatus.DISQUALIFIED},
    LeadStatus.CONTACT_FOUND: {LeadStatus.EXTRACTED, LeadStatus.DISQUALIFIED},
    LeadStatus.EXTRACTED: {LeadStatus.GENERATED, LeadStatus.DISQUALIFIED},
    LeadStatus.GENERATED: {LeadStatus.PENDING_REVIEW, LeadStatus.APPROVED},
    LeadStatus.PENDING_REVIEW: {LeadStatus.APPROVED, LeadStatus.REJECTED},
    LeadStatus.APPROVED: {LeadStatus.QUEUED, LeadStatus.REJECTED},
    LeadStatus.QUEUED: {LeadStatus.SENT, LeadStatus.REJECTED, LeadStatus.UNSUBSCRIBED},
    LeadStatus.SENT: {LeadStatus.REPLIED, LeadStatus.BOUNCED, LeadStatus.UNSUBSCRIBED, LeadStatus.EXPIRED},
    LeadStatus.REPLIED: {LeadStatus.WON, LeadStatus.LOST, LeadStatus.UNSUBSCRIBED},
    LeadStatus.BOUNCED: {LeadStatus.EXPIRED},
    LeadStatus.UNSUBSCRIBED: set(),
    LeadStatus.WON: set(),
    LeadStatus.LOST: {LeadStatus.EXPIRED},
    LeadStatus.EXPIRED: set(),
    LeadStatus.REJECTED: set(),
    LeadStatus.NO_CONTACT: set(),
    LeadStatus.DISQUALIFIED: set(),
}


class Base(DeclarativeBase):
    pass


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (UniqueConstraint("place_id", name="uq_leads_place_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    industry: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default=LeadStatus.DISCOVERED.value)
    status_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # --- discovery (Google Places). Only place_id may be stored permanently.
    place_id: Mapped[str] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(128))
    website: Mapped[str | None] = mapped_column(String(1024))
    domain: Mapped[str | None] = mapped_column(String(255), index=True)
    places_name: Mapped[str | None] = mapped_column(String(255))
    places_address: Mapped[str | None] = mapped_column(String(512))
    places_phone: Mapped[str | None] = mapped_column(String(64))
    places_rating: Mapped[float | None] = mapped_column(Float)
    places_rating_count: Mapped[int | None] = mapped_column(Integer)
    places_cached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- our own data, derived from the business's website (not Places)
    company_name: Mapped[str | None] = mapped_column(String(255))
    slug: Mapped[str | None] = mapped_column(String(160), unique=True)

    # --- scoring
    score: Mapped[int | None] = mapped_column(Integer)
    score_details: Mapped[dict | None] = mapped_column(JSON)
    findings: Mapped[list | None] = mapped_column(JSON)  # list[str], German sentences
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- contact
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    email_source_url: Mapped[str | None] = mapped_column(String(1024))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verification: Mapped[str | None] = mapped_column(String(64))  # syntax|mx|verified|invalid|unknown
    owner_name: Mapped[str | None] = mapped_column(String(255))
    owner_salutation: Mapped[str | None] = mapped_column(String(255))  # "Sehr geehrter Herr Müller"

    # --- extraction / generation / preview
    extracted: Mapped[dict | None] = mapped_column(JSON)
    generated: Mapped[dict | None] = mapped_column(JSON)
    validator_warnings: Mapped[list | None] = mapped_column(JSON)
    preview_path: Mapped[str | None] = mapped_column(String(255))
    preview_url: Mapped[str | None] = mapped_column(String(1024))
    preview_deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    screenshot_before: Mapped[str | None] = mapped_column(String(1024))
    screenshot_after: Mapped[str | None] = mapped_column(String(1024))

    # --- email / sending
    email_subject: Mapped[str | None] = mapped_column(String(255))
    email_body: Mapped[str | None] = mapped_column(Text)
    followup_1_body: Mapped[str | None] = mapped_column(Text)
    followup_2_body: Mapped[str | None] = mapped_column(Text)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sender_ref: Mapped[str | None] = mapped_column(String(255))  # e.g. Instantly lead id / .eml path
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reply_excerpt: Mapped[str | None] = mapped_column(Text)

    events: Mapped[list["LeadEvent"]] = relationship(back_populates="lead", cascade="all, delete-orphan")

    # ---------------------------------------------------------------- helpers
    @property
    def status_enum(self) -> LeadStatus:
        return LeadStatus(self.status)

    @property
    def display_name(self) -> str:
        return self.company_name or self.places_name or self.domain or f"Lead {self.id}"

    def transition(self, new_status: LeadStatus, reason: str | None = None, session: Session | None = None) -> None:
        current = self.status_enum
        if new_status not in ALLOWED_TRANSITIONS.get(current, set()):
            raise ValueError(f"illegal transition {current.value} -> {new_status.value} for lead {self.id}")
        self.status = new_status.value
        self.status_reason = reason
        self.updated_at = utcnow()
        ev = LeadEvent(lead=self, kind="status", payload={"from": current.value, "to": new_status.value, "reason": reason})
        if session is not None:
            session.add(ev)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Lead {self.id} {self.display_name} [{self.status}]>"


class LeadEvent(Base):
    __tablename__ = "lead_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    kind: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict | None] = mapped_column(JSON)

    lead: Mapped[Lead] = relationship(back_populates="events")


class Blocklist(Base):
    """Global suppression list. Matched on e-mail address *and* domain, across industries."""

    __tablename__ = "blocklist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[str] = mapped_column(String(255), unique=True)  # lower-cased email or domain
    kind: Mapped[str] = mapped_column(String(16))  # "email" | "domain"
    reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CostEntry(Base):
    """Every paid API call is recorded so `pipeline report` can show real costs."""

    __tablename__ = "costs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    service: Mapped[str] = mapped_column(String(32))  # places|pagespeed|llm|verifier|sender
    units: Mapped[float] = mapped_column(Float, default=1.0)
    eur: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str | None] = mapped_column(String(255))


class RunLog(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stage: Mapped[str] = mapped_column(String(32))
    summary: Mapped[dict | None] = mapped_column(JSON)


class SendCounter(Base):
    """Per-day counter of leads handed to the sender (daily limit + ramp)."""

    __tablename__ = "send_counters"

    day: Mapped[str] = mapped_column(String(10), primary_key=True)  # YYYY-MM-DD in Europe/Berlin
    count: Mapped[int] = mapped_column(Integer, default=0)


# ----------------------------------------------------------------- engine/session
_engine = None
_SessionLocal: sessionmaker | None = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = get_settings().database_url
        if url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        elif url.startswith("postgresql+psycopg"):
            # Supabase transaction pooler (port 6543) does not support server-side
            # prepared statements; psycopg 3 would start using them after 5 executions.
            connect_args = {"prepare_threshold": None}
        else:
            connect_args = {}
        _engine = create_engine(url, future=True, pool_pre_ping=True, connect_args=connect_args)
        if url.startswith("sqlite"):

            @event.listens_for(_engine, "connect")
            def _sqlite_pragmas(dbapi_conn, _):
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA journal_mode=WAL")
                cur.execute("PRAGMA foreign_keys=ON")
                cur.close()

        Base.metadata.create_all(_engine)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def reset_engine() -> None:
    """Used by tests to point at a fresh database."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


@contextmanager
def session_scope() -> Iterator[Session]:
    get_engine()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def leads_in_status(session: Session, status: LeadStatus, limit: int | None = None, industry: str | None = None) -> list[Lead]:
    stmt = select(Lead).where(Lead.status == status.value).order_by(Lead.id)
    if industry:
        stmt = stmt.where(Lead.industry == industry)
    if limit:
        stmt = stmt.limit(limit)
    return list(session.scalars(stmt))


def dump_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)
