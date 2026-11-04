"""Shared HTTP client with sane defaults (timeouts, UA, redirects captured)."""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from .config import get_settings


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    html: str
    headers: dict[str, str] = field(default_factory=dict)
    redirects: list[str] = field(default_factory=list)
    error: str | None = None
    elapsed_ms: int = 0

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status < 400


def client() -> httpx.Client:
    s = get_settings()
    return httpx.Client(
        timeout=httpx.Timeout(s.HTTP_TIMEOUT_SECONDS),
        follow_redirects=True,
        headers={"User-Agent": s.USER_AGENT, "Accept-Language": "de-DE,de;q=0.9"},
        verify=True,
    )


def fetch(url: str, c: httpx.Client | None = None) -> FetchResult:
    own = c is None
    c = c or client()
    try:
        r = c.get(url)
        redirects = [str(h.url) for h in r.history]
        text = r.text if "text" in r.headers.get("content-type", "text/html") else ""
        return FetchResult(
            url=url,
            final_url=str(r.url),
            status=r.status_code,
            html=text,
            headers={k.lower(): v for k, v in r.headers.items()},
            redirects=redirects,
            elapsed_ms=int(r.elapsed.total_seconds() * 1000) if r.elapsed else 0,
        )
    except httpx.HTTPError as e:
        return FetchResult(url=url, final_url=url, status=0, html="", error=f"{type(e).__name__}: {e}")
    finally:
        if own:
            c.close()
