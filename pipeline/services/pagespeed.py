"""PageSpeed Insights API v5 (mobile strategy) plus mock/null implementations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

from ..config import PROJECT_ROOT, get_settings
from ..costs import CostTracker
from ..log import get_logger
from ..util import retry

log = get_logger("pagespeed")


@dataclass
class PageSpeedResult:
    performance: float | None  # 0..1
    lcp_ms: float | None
    cls: float | None
    accessibility: float | None = None
    best_practices: float | None = None
    seo: float | None = None
    source: str = "psi"

    def as_dict(self) -> dict:
        return self.__dict__.copy()


class PageSpeedClient(Protocol):
    def analyze(self, url: str) -> PageSpeedResult | None: ...


class GooglePageSpeedClient:
    URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

    def __init__(self, api_key: str, costs: CostTracker):
        self.api_key = api_key
        self.costs = costs
        self.http = httpx.Client(timeout=120)

    @retry(times=2, base_delay=3, exceptions=(httpx.HTTPError,))
    def analyze(self, url: str) -> PageSpeedResult | None:
        s = get_settings()
        self.costs.check_requests("pagespeed", s.PAGESPEED_MAX_REQUESTS_PER_RUN)
        params = [("url", url), ("strategy", "mobile"), ("category", "performance"), ("category", "accessibility"), ("category", "best-practices"), ("category", "seo")]
        if self.api_key:
            params.append(("key", self.api_key))
        r = self.http.get(self.URL, params=params)
        self.costs.record("pagespeed", s.COST_PAGESPEED_PER_REQUEST_EUR, note=url)
        if r.status_code >= 500 or r.status_code == 429:
            r.raise_for_status()
        if r.status_code >= 400:
            log.warning("pagespeed failed", url=url, status=r.status_code, body=r.text[:200])
            return None
        data = r.json()
        lh = data.get("lighthouseResult", {})
        cats = lh.get("categories", {})
        audits = lh.get("audits", {})

        def score(cat: str) -> float | None:
            v = (cats.get(cat) or {}).get("score")
            return float(v) if v is not None else None

        return PageSpeedResult(
            performance=score("performance"),
            lcp_ms=(audits.get("largest-contentful-paint") or {}).get("numericValue"),
            cls=(audits.get("cumulative-layout-shift") or {}).get("numericValue"),
            accessibility=score("accessibility"),
            best_practices=score("best-practices"),
            seo=score("seo"),
        )


class MockPageSpeedClient:
    """Reads fixtures/pagespeed.json keyed by the fixture folder name in the URL."""

    def __init__(self, fixtures_file: Path | None = None):
        self.data = json.loads((fixtures_file or PROJECT_ROOT / "fixtures" / "pagespeed.json").read_text(encoding="utf-8"))

    def analyze(self, url: str) -> PageSpeedResult | None:
        for key, v in self.data.items():
            if f"/{key}/" in url or url.rstrip("/").endswith(key):
                return PageSpeedResult(source="mock", **v)
        return None


class NullPageSpeedClient:
    def analyze(self, url: str) -> PageSpeedResult | None:
        return None


def make_pagespeed_client(costs: CostTracker, mock: bool = False) -> PageSpeedClient:
    s = get_settings()
    if mock:
        return MockPageSpeedClient()
    # PSI works without a key at a low quota; a key raises the quota. Either way it is free.
    return GooglePageSpeedClient(s.PAGESPEED_API_KEY, costs)
