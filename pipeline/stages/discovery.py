"""Stage 1 – Discovery via Google Places Text Search (or the offline mock)."""

from __future__ import annotations

from collections import Counter
from datetime import timedelta

from sqlalchemy import select

from ..config import get_settings
from ..costs import BudgetExceeded, CostTracker
from ..db import Lead, LeadStatus, SearchLog, session_scope, utcnow
from ..industry import load_industry
from ..log import get_logger
from ..services import blocklist as bl
from ..services.places import Place, PlacesClient, make_places_client
from ..util import normalize_url, read_list_file, registered_domain

log = get_logger("discovery")


def classify_place(p: Place, platform_domains: set[str], chain_domains: set[str]) -> tuple[str | None, str | None]:
    """Return (domain, disqualify_reason). domain is None when the place has no own website."""
    if (p.business_status or "OPERATIONAL") == "CLOSED_PERMANENTLY":
        return None, "dauerhaft geschlossen"
    if not p.website:
        return None, "keine Website"
    domain = registered_domain(p.website)
    if not domain or "." not in domain:
        return None, "ungültige Website-URL"
    if domain in platform_domains:
        return domain, f"Fremdplattform ({domain})"
    if domain in chain_domains:
        return domain, f"Kette/Franchise ({domain})"
    return domain, None


def run(limit: int | None = None, cities: list[str] | None = None, costs: CostTracker | None = None, client: PlacesClient | None = None) -> dict:
    s = get_settings()
    industry = load_industry()
    costs = costs or CostTracker()
    client = client or make_places_client(costs)
    if client is None:
        log.warning("GOOGLE_PLACES_API_KEY fehlt – Discovery übersprungen (Demo: `pipeline demo`).")
        return {"skipped": "no GOOGLE_PLACES_API_KEY"}

    cities = cities or read_list_file(s.REGION_CITIES_FILE)
    platform = bl.platform_domains()
    chains = bl.chain_domains()
    stats = Counter()
    new_leads = 0

    with session_scope() as session:
        known_place_ids = set(session.scalars(select(Lead.place_id)))
        domain_counts = Counter(d for d in session.scalars(select(Lead.domain)) if d)
        for city in cities:
            for term in industry.search_terms:
                query = term.format(city=city)
                logged = session.get(SearchLog, query)
                if logged is not None and _aware(logged.searched_at) > utcnow() - timedelta(days=s.PLACES_RESEARCH_DAYS):
                    stats["skipped_recent_query"] += 1
                    continue
                try:
                    places = list(client.search(query, s.PLACES_PAGES_PER_QUERY))
                except BudgetExceeded as e:
                    log.warning(str(e))
                    stats["budget_stop"] += 1
                    return _finish(stats, new_leads)
                for p in places:
                    stats["seen"] += 1
                    if p.place_id in known_place_ids:
                        stats["dup_place_id"] += 1
                        continue
                    known_place_ids.add(p.place_id)
                    domain, reason = classify_place(p, platform, chains)
                    if reason and domain is None:
                        stats["excluded_no_site"] += 1
                        continue  # not worth a row: nothing to contact
                    if domain and domain_counts[domain] >= 1 and reason is None:
                        # second location with the same website -> treat as duplicate, count towards chain heuristic
                        domain_counts[domain] += 1
                        stats["dup_domain"] += 1
                        if domain_counts[domain] >= s.CHAIN_MIN_LOCATIONS:
                            _disqualify_domain(session, domain, "Kette (mehrere Standorte, gleiche Domain)")
                        continue
                    domain_counts[domain or ""] += 1
                    lead = Lead(
                        industry=industry.name,
                        place_id=p.place_id,
                        city=city,
                        website=normalize_url(p.website or ""),
                        domain=domain,
                        places_name=p.name,
                        places_address=p.address,
                        places_phone=p.phone,
                        places_rating=p.rating,
                        places_rating_count=p.rating_count,
                        places_cached_at=utcnow(),
                        status=LeadStatus.DISCOVERED.value,
                    )
                    session.add(lead)
                    session.flush()
                    if reason:
                        lead.transition(LeadStatus.DISQUALIFIED, reason, session)
                        stats["disqualified"] += 1
                    elif bl.is_blocked(session, domain=domain):
                        lead.transition(LeadStatus.DISQUALIFIED, "auf Sperrliste", session)
                        stats["blocked"] += 1
                    else:
                        new_leads += 1
                    if limit and new_leads >= limit and p is not places[-1]:
                        return _finish(stats, new_leads)  # query not fully processed -> repeat next run
                # every result of this query was handled: remember it
                if logged is None:
                    session.add(SearchLog(query=query, searched_at=utcnow(), results=len(places)))
                else:
                    logged.searched_at, logged.results = utcnow(), len(places)
                session.flush()
                if limit and new_leads >= limit:
                    return _finish(stats, new_leads)
    return _finish(stats, new_leads)


def _aware(dt):
    from datetime import timezone

    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _disqualify_domain(session, domain: str, reason: str) -> None:
    for lead in session.scalars(select(Lead).where(Lead.domain == domain, Lead.status.in_([LeadStatus.DISCOVERED.value, LeadStatus.SCORED.value, LeadStatus.QUALIFIED.value]))):
        lead.transition(LeadStatus.DISQUALIFIED, reason, session)


def _finish(stats: Counter, new_leads: int) -> dict:
    out = dict(stats)
    out["new_leads"] = new_leads
    log.info("discovery done", **out)
    return out
