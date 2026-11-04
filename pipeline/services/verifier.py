"""E-mail verification: syntax, MX lookup and an optional external verifier (MillionVerifier)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

import httpx

from ..config import get_settings
from ..costs import CostTracker
from ..log import get_logger

log = get_logger("verifier")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
ROLE_PREFIXES = ("noreply", "no-reply", "donotreply", "postmaster", "abuse", "webmaster@1und1", "hostmaster")


@dataclass
class Verification:
    email: str
    syntax_ok: bool
    mx_ok: bool | None  # None = not checked
    verified: bool | None  # None = no external verifier
    status: str  # verified | mx | syntax | invalid | unknown
    detail: str | None = None

    @property
    def sendable(self) -> bool:
        s = get_settings()
        if not self.syntax_ok or self.mx_ok is False or self.verified is False:
            return False
        if s.REQUIRE_VERIFIED_EMAIL:
            return self.verified is True
        return True


def syntax_valid(email: str) -> bool:
    e = email.strip().lower()
    return bool(EMAIL_RE.match(e)) and not e.startswith(ROLE_PREFIXES) and ".." not in e


def mx_exists(domain: str) -> bool | None:
    try:
        import dns.resolver  # type: ignore
    except ImportError:  # pragma: no cover
        return None
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        return len(list(answers)) > 0
    except dns.resolver.NoAnswer:
        try:
            dns.resolver.resolve(domain, "A", lifetime=5)
            return True  # implicit MX via A record
        except Exception:
            return False
    except dns.resolver.NXDOMAIN:
        return False
    except Exception as e:  # timeout, no network
        log.debug("mx lookup failed", domain=domain, err=str(e))
        return None


class ExternalVerifier(Protocol):
    def verify(self, email: str) -> bool | None: ...


class MillionVerifierClient:
    URL = "https://api.millionverifier.com/api/v3/"

    def __init__(self, api_key: str, costs: CostTracker):
        self.api_key = api_key
        self.costs = costs
        self.http = httpx.Client(timeout=30)

    def verify(self, email: str) -> bool | None:
        try:
            r = self.http.get(self.URL, params={"api": self.api_key, "email": email, "timeout": 10})
            self.costs.record("verifier", 0.0003, note=email)  # ~0.3 €/1000
            data = r.json()
        except Exception as e:
            log.warning("verifier error", err=str(e))
            return None
        result = (data.get("result") or "").lower()
        if result == "ok":
            return True
        if result in {"invalid", "disposable"}:
            return False
        return None  # catch_all / unknown


def verify_email(email: str, costs: CostTracker, external: ExternalVerifier | None = None, *, offline: bool = False) -> Verification:
    s = get_settings()
    email = email.strip().lower()
    if not syntax_valid(email):
        return Verification(email, False, None, None, "invalid", "syntax")
    mx: bool | None = None
    if s.MX_CHECK and not offline:
        mx = mx_exists(email.split("@", 1)[1])
        if mx is False:
            return Verification(email, True, False, None, "invalid", "no MX")
    ext: bool | None = None
    if external is not None:
        ext = external.verify(email)
    if ext is True:
        status = "verified"
    elif ext is False:
        status = "invalid"
    elif mx:
        status = "mx"
    elif offline:
        status = "unknown"
    else:
        status = "syntax"
    return Verification(email, True, mx, ext, status)


def make_external_verifier(costs: CostTracker) -> ExternalVerifier | None:
    s = get_settings()
    if s.MILLIONVERIFIER_API_KEY:
        return MillionVerifierClient(s.MILLIONVERIFIER_API_KEY, costs)
    return None
