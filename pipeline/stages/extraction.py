"""Stage 4 – Extraction: crawl the old website and collect raw, sourced data.

Output (`lead.extracted`) is a JSON document with every page's text, plus
regex-found *candidates* (licence classes, prices, hours, team names, phone,
images). Candidates always carry the source URL. The generation stage (LLM or
composer) only ever uses this document.
"""

from __future__ import annotations

import re
from typing import Any

from ..config import get_settings
from ..crawl import Page, crawl_site
from ..db import Lead, LeadStatus, leads_in_status, session_scope
from ..industry import load_industry
from ..log import get_logger
from ..util import collapse_ws, same_site

log = get_logger("extraction")

CLASS_RE = re.compile(r"\bKlasse[n]?\s+((?:A1|A2|AM|A|B196|B197|BE|B|C1E|C1|CE|C|D1E|D1|DE|D|L|T)(?:\s*[,/und&]+\s*(?:A1|A2|AM|A|B196|B197|BE|B|C1E|C1|CE|C|D1E|D1|DE|D|L|T))*)\b")
CLASS_TOKEN_RE = re.compile(r"\b(A1|A2|AM|A|B196|B197|BE|B|C1E|C1|CE|C|D1E|D1|DE|D|L|T)\b")
PRICE_LINE_RE = re.compile(r"^(?P<label>[^\n€]{3,80}?)\s*[:\-–]?\s*(?P<price>\d{1,4}(?:[.,]\d{2})?\s?(?:€|EUR|Euro))\s*$", re.M)
PRICE_ANY_RE = re.compile(r"\d{1,4}(?:[.,]\d{2})?\s?(?:€|EUR|Euro)")
DAY = r"(?:Mo|Di|Mi|Do|Fr|Sa|So|Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag)"
HOURS_RE = re.compile(rf"({DAY}\.?(?:\s*(?:[-–]|bis|und|,|\+)\s*{DAY}\.?)*\s*:?\s*\d{{1,2}}[:.]\d{{2}}\s*(?:[-–]|bis)\s*\d{{1,2}}[:.]\d{{2}}(?:\s*(?:Uhr|h))?(?:\s*(?:und|,|&)\s*\d{{1,2}}[:.]\d{{2}}\s*(?:[-–]|bis)\s*\d{{1,2}}[:.]\d{{2}}(?:\s*(?:Uhr|h))?)?)")
NAME_LINE_RE = re.compile(r"^[ \t]*([A-ZÄÖÜ][^\W\d_]+(?:-[A-ZÄÖÜ][^\W\d_]+)?(?:[ \t]+[A-ZÄÖÜ][^\W\d_]+(?:-[A-ZÄÖÜ][^\W\d_]+)?){1,2})[ \t]*[-–:,(][ \t]*([^\n]{3,60}?)\)?[ \t]*$", re.M)
TEAM_ROLES = ("fahrlehrer", "fahrlehrerin", "inhaber", "inhaberin", "büro", "buero", "ausbilder", "ausbilderin", "geschäftsführ", "leitung", "verwaltung")


def _section_heading(text: str, pos: int) -> str:
    """Nearest preceding short line – used as label for hour blocks."""
    before = text[:pos].splitlines()
    for line in reversed(before[-6:]):
        line = collapse_ws(line)
        if 3 <= len(line) <= 40 and not re.search(r"\d{1,2}[:.]\d{2}", line):
            return line.strip(" :")
    return "Öffnungszeiten"


def extract_candidates(pages: list[Page], domain: str) -> dict[str, Any]:
    classes: dict[str, dict] = {}
    prices: list[dict] = []
    hours: list[dict] = []
    team: list[dict] = []
    phones: list[dict] = []
    emails: list[dict] = []
    images: list[dict] = []
    addresses: list[dict] = []
    seen_hours: set[str] = set()

    for p in pages:
        text = p.text
        for m in CLASS_RE.finditer(text):
            for tok in CLASS_TOKEN_RE.findall(m.group(1)):
                key = tok.upper()
                if key not in classes:
                    start = max(0, m.start() - 10)
                    classes[key] = {"name": f"Klasse {key}", "source": p.url, "snippet": collapse_ws(text[start : m.end() + 120])}
        for m in PRICE_LINE_RE.finditer(text):
            label = collapse_ws(m.group("label")).strip(" .:-–")
            price = collapse_ws(m.group("price"))
            if 2 < len(label) < 80:
                prices.append({"label": label, "price": price, "source": p.url, "snippet": collapse_ws(m.group(0))})
        for m in HOURS_RE.finditer(text):
            entry = collapse_ws(m.group(1))
            if entry in seen_hours:
                continue
            seen_hours.add(entry)
            hours.append({"label": _section_heading(text, m.start()), "entry": entry, "source": p.url, "snippet": entry})
        if p.kind in ("team", "about", "start"):
            for m in NAME_LINE_RE.finditer(text):
                name, role = collapse_ws(m.group(1)), collapse_ws(m.group(2) or "")
                if role and any(r in role.lower() for r in TEAM_ROLES) and name not in [t["name"] for t in team]:
                    team.append({"name": name, "role": role, "source": p.url, "snippet": collapse_ws(m.group(0))})
        for ph in p.phones:
            if ph not in [x["value"] for x in phones]:
                phones.append({"value": ph, "source": p.url})
        for e in p.emails:
            if e not in [x["value"] for x in emails]:
                emails.append({"value": e, "source": p.url})
        for url, alt in p.images:
            if same_site(url, domain) and url not in [i["url"] for i in images] and not re.search(r"(icon|logo-?klein|spacer|pixel|button|\.gif$|1x1)", url, re.I):
                role = "logo" if re.search(r"logo", url + " " + alt, re.I) else "gallery"
                images.append({"url": url, "alt": alt, "role": role, "source": p.url})
        if p.kind in ("imprint", "contact", "start"):
            m = re.search(r"([A-ZÄÖÜ][\w.\-äöüß ]{1,40}?(?i:straße|strasse|str\.|weg|platz|allee|ring|gasse|damm|ufer|markt|chaussee)[ \t]*\d+[a-z]?)[ \t]*,?[ \t]*\n?[ \t]*(\d{5})[ \t]+([A-ZÄÖÜ][^\W\d_\n]+(?:[ \-][A-ZÄÖÜ(][^\W\d_)\n]+)?)", p.text)
            if m:
                addr = f"{collapse_ws(m.group(1))}, {m.group(2)} {collapse_ws(m.group(3))}"
                if addr not in [a["value"] for a in addresses]:
                    addresses.append({"value": addr, "source": p.url, "snippet": collapse_ws(m.group(0))})

    # de-duplicate prices by label
    uniq: dict[str, dict] = {}
    for pr in prices:
        uniq.setdefault(pr["label"].lower(), pr)
    return {
        "classes": list(classes.values()),
        "prices": list(uniq.values())[:20],
        "hours": hours[:12],
        "team": team[:12],
        "phones": phones,
        "emails": emails,
        "addresses": addresses,
        "images": images[: get_settings().EXTRACT_MAX_IMAGES],
    }


def probe_images(images: list[dict], min_width: int = 900, min_height: int = 500, max_bytes: int = 4_000_000) -> list[dict]:
    """Download candidate images and keep only those large enough for a hero/gallery (needs Pillow)."""
    try:
        from io import BytesIO

        from PIL import Image
    except ImportError:  # pragma: no cover
        return images
    from ..http import client as http_client

    kept: list[dict] = []
    with http_client() as http:
        for img in images:
            try:
                r = http.get(img["url"])
                if r.status_code != 200 or len(r.content) > max_bytes:
                    continue
                with Image.open(BytesIO(r.content)) as im:
                    w, h = im.size
            except Exception:
                continue
            if img.get("role") == "logo":
                if w >= 80 and h >= 30:
                    kept.append({**img, "width": w, "height": h})
            elif w >= min_width and h >= min_height:
                kept.append({**img, "width": w, "height": h})
    return kept


def extract_site(website: str, domain: str, keywords: dict, max_pages: int, use_playwright: bool) -> dict[str, Any]:
    pages = crawl_site(website, domain, keywords, {"services", "prices", "team", "hours", "about", "contact", "imprint", "start"}, max_pages=max_pages, use_playwright=use_playwright)
    candidates = extract_candidates(pages, domain)
    candidates["images"] = probe_images(candidates["images"])
    data = {
        "website": website,
        "domain": domain,
        "pages": [{"url": p.url, "kind": p.kind, "title": p.title, "text": p.text[:12000]} for p in pages],
        "candidates": candidates,
    }
    data["source_text"] = "\n\n".join(f"### {p.url}\n{p.text}" for p in pages)
    return data


def run(limit: int | None = None) -> dict:
    s = get_settings()
    industry = load_industry()
    stats = {"extracted": 0, "failed": 0}
    with session_scope() as session:
        ids = [l.id for l in leads_in_status(session, LeadStatus.CONTACT_FOUND, limit, industry.name)]
    for lead_id in ids:
        with session_scope() as session:
            lead = session.get(Lead, lead_id)
            try:
                data = extract_site(lead.website, lead.domain, industry.page_keywords, s.EXTRACT_MAX_PAGES, s.EXTRACT_USE_PLAYWRIGHT)
            except Exception as e:
                log.error("extraction failed", lead=lead_id, err=str(e))
                stats["failed"] += 1
                continue
            if not data["pages"]:
                lead.transition(LeadStatus.DISQUALIFIED, "Website beim Extrahieren nicht erreichbar", session)
                stats["failed"] += 1
                continue
            lead.extracted = data
            lead.transition(LeadStatus.EXTRACTED, f"{len(data['pages'])} Seiten", session)
            stats["extracted"] += 1
            log.info("extracted", lead=lead_id, pages=len(data["pages"]), classes=len(data["candidates"]["classes"]), prices=len(data["candidates"]["prices"]))
    log.info("extraction done", **stats)
    return stats
