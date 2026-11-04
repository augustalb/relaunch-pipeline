"""Global suppression list: e-mail addresses and domains that must never be contacted again."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import PROJECT_ROOT, get_settings
from ..db import Blocklist
from ..util import read_list_file, registered_domain


def _norm(value: str) -> tuple[str, str]:
    v = value.strip().lower()
    if "@" in v:
        return v, "email"
    return registered_domain(v), "domain"


def add(session: Session, value: str, reason: str | None = None) -> bool:
    v, kind = _norm(value)
    if not v:
        return False
    if session.scalar(select(Blocklist).where(Blocklist.value == v)):
        return False
    session.add(Blocklist(value=v, kind=kind, reason=reason))
    session.flush()
    return True


def block_contact(session: Session, email: str | None, domain: str | None, reason: str) -> None:
    """Block both the address and its domain (and the website domain if different)."""
    if email:
        add(session, email, reason)
        add(session, email.split("@", 1)[1], reason)
    if domain:
        add(session, domain, reason)


def is_blocked(session: Session, email: str | None = None, domain: str | None = None) -> bool:
    candidates: set[str] = set()
    if email:
        e = email.strip().lower()
        candidates.add(e)
        candidates.add(registered_domain(e.split("@", 1)[1]))
    if domain:
        candidates.add(registered_domain(domain))
    candidates.discard("")
    if not candidates:
        return False
    hit = session.scalar(select(Blocklist.id).where(Blocklist.value.in_(candidates)).limit(1))
    return hit is not None


def sync_manual_file(session: Session) -> int:
    """Import entries from config/blocklist_manual.txt (idempotent)."""
    n = 0
    for entry in read_list_file(PROJECT_ROOT / "config" / "blocklist_manual.txt"):
        if add(session, entry, "manual"):
            n += 1
    return n


def chain_domains() -> set[str]:
    return {registered_domain(d) for d in read_list_file(PROJECT_ROOT / "config" / "blocklist_domains.txt")}


def platform_domains() -> set[str]:
    return {registered_domain(d) for d in read_list_file(PROJECT_ROOT / "config" / "platform_domains.txt")}


_ = get_settings
