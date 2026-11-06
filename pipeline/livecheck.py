"""Live credential checks for `pipeline doctor --live`.

Each check makes one request that costs nothing:
- Database: `SELECT 1` (also creates missing tables via get_engine()).
- Google Places: Text Search with field mask `places.id` only (IDs-only SKU, not billed).
- PageSpeed Insights: one mobile run against example.com (free API).
- Anthropic: list models (free) and one tiny structured-output request with the real schema (< 0.01 cent).
- Cloudflare: list Pages projects of the account (checks account ID and token permission).

Key values are never printed; error bodies are truncated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import httpx

from .config import get_settings


@dataclass
class CheckResult:
    name: str
    status: str  # "ok" | "fehler" | "nicht gesetzt"
    detail: str = ""

    @property
    def failed(self) -> bool:
        return self.status == "fehler"


def _short(r: httpx.Response) -> str:
    return f"HTTP {r.status_code}: {r.text[:160].strip()}"


def check_database() -> CheckResult:
    from sqlalchemy import text

    from .db import get_engine

    s = get_settings()
    where = s.database_url.split("@")[-1] if "@" in s.database_url else s.database_url
    try:
        with get_engine().connect() as c:
            c.execute(text("select 1")).scalar()
        return CheckResult("Datenbank", "ok", where)
    except Exception as e:  # noqa: BLE001 - report any driver error as a failed check
        return CheckResult("Datenbank", "fehler", f"{where}: {type(e).__name__}: {str(e)[:160]}")


def check_places(c: httpx.Client) -> CheckResult:
    key = get_settings().GOOGLE_PLACES_API_KEY
    if not key:
        return CheckResult("Google Places", "nicht gesetzt")
    r = c.post(
        "https://places.googleapis.com/v1/places:searchText",
        headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": "places.id"},
        json={"textQuery": "Fahrschule Köln", "pageSize": 1, "languageCode": "de"},
    )
    if r.status_code == 200:
        return CheckResult("Google Places", "ok", f"{len(r.json().get('places', []))} Treffer (nur ID, kostenlos)")
    return CheckResult("Google Places", "fehler", _short(r))


def check_pagespeed(c: httpx.Client) -> CheckResult:
    key = get_settings().PAGESPEED_API_KEY
    if not key:
        return CheckResult("PageSpeed", "nicht gesetzt")
    r = c.get(
        "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
        params={"url": "https://example.com/", "strategy": "mobile", "key": key},
        timeout=90,
    )
    if r.status_code == 200:
        score = (r.json().get("lighthouseResult", {}).get("categories", {}).get("performance", {}) or {}).get("score")
        return CheckResult("PageSpeed", "ok", f"example.com mobil: {round(score * 100) if score is not None else '?'}")
    return CheckResult("PageSpeed", "fehler", _short(r))


def check_anthropic(c: httpx.Client) -> CheckResult:
    s = get_settings()
    if not s.ANTHROPIC_API_KEY:
        return CheckResult("Anthropic", "nicht gesetzt")
    r = c.get(
        "https://api.anthropic.com/v1/models",
        headers={"x-api-key": s.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
    )
    if r.status_code != 200:
        return CheckResult("Anthropic", "fehler", _short(r))
    ids = [m.get("id", "") for m in r.json().get("data", [])]
    if s.LLM_MODEL not in ids:
        return CheckResult("Anthropic", "fehler", f"{s.LLM_MODEL} NICHT in der Modellliste")
    # The real generation schema must be accepted by structured outputs (a 400 here broke every LLM generation once).
    from .schema import json_schema_for_llm

    r = c.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": s.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
        json={
            "model": s.LLM_MODEL,
            "max_tokens": 64,
            "messages": [{"role": "user", "content": "Schema check only. Fill minimal placeholder values."}],
            "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": json_schema_for_llm()}},
        },
        timeout=60,
    )
    if r.status_code != 200:
        return CheckResult("Anthropic", "fehler", "Schema abgelehnt: " + _short(r))
    return CheckResult("Anthropic", "ok", f"{s.LLM_MODEL} verfügbar, Schema akzeptiert (<0,01 Cent)")


def check_cloudflare(c: httpx.Client) -> CheckResult:
    s = get_settings()
    if not (s.CLOUDFLARE_API_TOKEN and s.CLOUDFLARE_ACCOUNT_ID):
        return CheckResult("Cloudflare", "nicht gesetzt")
    r = c.get(
        f"https://api.cloudflare.com/client/v4/accounts/{s.CLOUDFLARE_ACCOUNT_ID}/pages/projects",
        headers={"Authorization": f"Bearer {s.CLOUDFLARE_API_TOKEN}"},
    )
    if r.status_code == 200 and r.json().get("success"):
        names = [p.get("name") for p in r.json().get("result", [])]
        exists = s.CLOUDFLARE_PAGES_PROJECT in names
        return CheckResult(
            "Cloudflare",
            "ok",
            f"Pages-Zugriff ok, Projekt {s.CLOUDFLARE_PAGES_PROJECT} {'vorhanden' if exists else 'wird beim ersten Deploy angelegt'}",
        )
    return CheckResult("Cloudflare", "fehler", _short(r))


HTTP_CHECKS: list[Callable[[httpx.Client], CheckResult]] = [
    check_places,
    check_pagespeed,
    check_anthropic,
    check_cloudflare,
]


def run_live_checks(client: httpx.Client | None = None) -> list[CheckResult]:
    results = [check_database()]
    own = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(30.0))
    try:
        for fn in HTTP_CHECKS:
            try:
                results.append(fn(client))
            except httpx.HTTPError as e:
                results.append(CheckResult(fn.__name__.removeprefix("check_"), "fehler", f"{type(e).__name__}: {e}"))
    finally:
        if own:
            client.close()
    return results
