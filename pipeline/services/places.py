"""Google Places API (New) – Text Search with field masks – plus an offline mock.

Google Maps Platform ToS: place IDs may be stored indefinitely; other Places
content may be cached for up to 30 days. `pipeline.stages.discovery` therefore
records `places_cached_at` and `pipeline.stages.housekeeping` scrubs cached
fields older than PLACES_CACHE_DAYS.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Protocol

import httpx

from ..config import PROJECT_ROOT, get_settings
from ..costs import CostTracker
from ..log import get_logger
from ..util import retry

log = get_logger("places")

FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.nationalPhoneNumber",
        "places.websiteUri",
        "places.rating",
        "places.userRatingCount",
        "places.businessStatus",
        "nextPageToken",
    ]
)


@dataclass
class Place:
    place_id: str
    name: str
    address: str | None
    phone: str | None
    website: str | None
    rating: float | None
    rating_count: int | None
    business_status: str | None  # OPERATIONAL | CLOSED_TEMPORARILY | CLOSED_PERMANENTLY


class PlacesClient(Protocol):
    def search(self, query: str, max_pages: int) -> Iterator[Place]: ...


class GooglePlacesClient:
    URL = "https://places.googleapis.com/v1/places:searchText"

    def __init__(self, api_key: str, costs: CostTracker):
        self.api_key = api_key
        self.costs = costs
        self.http = httpx.Client(timeout=30)

    @retry(times=3, base_delay=1.5, exceptions=(httpx.HTTPError,))
    def _post(self, body: dict) -> dict:
        s = get_settings()
        self.costs.check_requests("places", s.PLACES_MAX_REQUESTS_PER_RUN)
        r = self.http.post(
            self.URL,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": FIELD_MASK,
            },
            json=body,
        )
        self.costs.record("places", s.COST_PLACES_PER_REQUEST_EUR, note=body.get("textQuery"))
        if r.status_code == 429 or r.status_code >= 500:
            r.raise_for_status()
        if r.status_code >= 400:
            log.error("places error", status=r.status_code, body=r.text[:300])
            return {}
        return r.json()

    def search(self, query: str, max_pages: int) -> Iterator[Place]:
        body: dict = {"textQuery": query, "languageCode": "de", "regionCode": "DE", "pageSize": 20}
        for _ in range(max_pages):
            data = self._post(body)
            for p in data.get("places", []):
                yield Place(
                    place_id=p["id"],
                    name=(p.get("displayName") or {}).get("text", ""),
                    address=p.get("formattedAddress"),
                    phone=p.get("nationalPhoneNumber"),
                    website=p.get("websiteUri"),
                    rating=p.get("rating"),
                    rating_count=p.get("userRatingCount"),
                    business_status=p.get("businessStatus"),
                )
            token = data.get("nextPageToken")
            if not token:
                break
            body["pageToken"] = token


class MockPlacesClient:
    """Serves the local HTML fixtures as if Google had found them (demo / tests)."""

    def __init__(self, base_url: str, fixtures_file: Path | None = None):
        self.base_url = base_url.rstrip("/")
        self.fixtures_file = fixtures_file or PROJECT_ROOT / "fixtures" / "places.json"

    def search(self, query: str, max_pages: int) -> Iterator[Place]:
        data = json.loads(self.fixtures_file.read_text(encoding="utf-8"))
        city = query.split(" in ")[-1].strip() if " in " in query else query.split()[-1]
        for entry in data:
            if entry.get("city", "").lower() != city.lower():
                continue
            website = entry.get("website")
            if website and website.startswith("/"):
                website = self.base_url + website
            yield Place(
                place_id=entry["place_id"],
                name=entry["name"],
                address=entry.get("address"),
                phone=entry.get("phone"),
                website=website,
                rating=entry.get("rating"),
                rating_count=entry.get("rating_count"),
                business_status=entry.get("business_status", "OPERATIONAL"),
            )


def make_places_client(costs: CostTracker, mock_base_url: str | None = None) -> PlacesClient | None:
    s = get_settings()
    if mock_base_url:
        return MockPlacesClient(mock_base_url)
    if s.GOOGLE_PLACES_API_KEY:
        return GooglePlacesClient(s.GOOGLE_PLACES_API_KEY, costs)
    return None
