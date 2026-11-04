"""Stage 3 – Contact: crawl imprint/contact/privacy pages, extract e-mail + owner, verify."""

from __future__ import annotations

from ..config import get_settings
from ..costs import CostTracker
from ..crawl import crawl_site
from ..db import Lead, LeadStatus, leads_in_status, session_scope
from ..industry import load_industry
from ..log import get_logger
from ..names import extract_company_name, extract_owner
from ..services import blocklist as bl
from ..services.verifier import ExternalVerifier, make_external_verifier, verify_email
from ..util import registered_domain

log = get_logger("contact")


def pick_email(emails: list[tuple[str, str]], domain: str) -> tuple[str, str] | None:
    """Prefer addresses on the business's own domain, then generic providers; return (email, source_url)."""
    own = [(e, u) for e, u in emails if registered_domain(e.split("@", 1)[1]) == domain]
    pref_order = ("info@", "kontakt@", "mail@", "post@", "office@", "hallo@", "fahrschule@")
    for prefix in pref_order:
        for e, u in own:
            if e.startswith(prefix):
                return e, u
    if own:
        return own[0]
    return emails[0] if emails else None


def find_contact(website: str, domain: str, keywords: dict, max_pages: int = 4, use_playwright: bool | None = None) -> dict:
    if use_playwright is None:
        use_playwright = get_settings().EXTRACT_USE_PLAYWRIGHT
    pages = crawl_site(website, domain, keywords, {"imprint", "contact"}, max_pages=max_pages, use_playwright=use_playwright)
    emails: list[tuple[str, str]] = []
    owner = salutation = company = None
    for p in sorted(pages, key=lambda p: {"imprint": 0, "contact": 1}.get(p.kind, 2)):
        for e in p.emails:
            if (e, p.url) not in emails and e not in [x for x, _ in emails]:
                emails.append((e, p.url))
        if owner is None and p.kind in ("imprint", "contact", "start"):
            owner, salutation = extract_owner(p.text)
        if company is None and p.kind in ("imprint", "contact"):
            company = extract_company_name(p.text, None)
    chosen = pick_email(emails, domain)
    return {"email": chosen[0] if chosen else None, "email_source_url": chosen[1] if chosen else None, "owner": owner, "salutation": salutation, "company": company, "pages": len(pages), "all_emails": [e for e, _ in emails]}


def run(limit: int | None = None, costs: CostTracker | None = None, offline: bool = False, external: ExternalVerifier | None = None) -> dict:
    s = get_settings()
    industry = load_industry()
    costs = costs or CostTracker()
    external = external or make_external_verifier(costs)
    stats = {"contact_found": 0, "no_contact": 0, "blocked": 0, "unverified": 0}
    with session_scope() as session:
        ids = [l.id for l in leads_in_status(session, LeadStatus.QUALIFIED, limit, industry.name)]
    for lead_id in ids:
        with session_scope() as session:
            lead = session.get(Lead, lead_id)
            try:
                info = find_contact(lead.website, lead.domain, industry.page_keywords)
            except Exception as e:
                log.error("contact crawl failed", lead=lead_id, err=str(e))
                lead.transition(LeadStatus.NO_CONTACT, f"Crawl-Fehler: {e}", session)
                stats["no_contact"] += 1
                continue
            lead.owner_name = info["owner"]
            lead.owner_salutation = info["salutation"]
            lead.company_name = info["company"] or lead.places_name
            if not info["email"]:
                lead.transition(LeadStatus.NO_CONTACT, "keine E-Mail-Adresse gefunden", session)
                stats["no_contact"] += 1
                continue
            if bl.is_blocked(session, email=info["email"], domain=lead.domain):
                lead.transition(LeadStatus.DISQUALIFIED, "auf Sperrliste", session)
                stats["blocked"] += 1
                continue
            v = verify_email(info["email"], costs, external, offline=offline)
            lead.email = v.email
            lead.email_source_url = info["email_source_url"]
            lead.email_verification = v.status
            lead.email_verified = v.verified is True
            if v.status == "invalid":
                lead.transition(LeadStatus.NO_CONTACT, f"E-Mail ungültig ({v.detail or v.status})", session)
                stats["no_contact"] += 1
                continue
            if s.REQUIRE_VERIFIED_EMAIL and not lead.email_verified and not offline:
                stats["unverified"] += 1
            lead.transition(LeadStatus.CONTACT_FOUND, f"{v.email} ({v.status})", session)
            stats["contact_found"] += 1
            log.info("contact found", lead=lead_id, email=v.email, status=v.status, owner=info["owner"])
    log.info("contact done", **stats)
    return stats
