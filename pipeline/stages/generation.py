"""Stage 5 – Generation: fill the strict `SiteContent` schema from extracted data.

Two paths, same output:

* `compose_from_extracted` – deterministic, no LLM. Used without an API key and
  as the fallback when the LLM output fails validation twice.
* `generate_with_llm` – Anthropic structured output, validated by pydantic and
  the hallucination validator.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from ..config import get_settings
from ..costs import BudgetExceeded, CostTracker
from ..db import Lead, LeadStatus, leads_in_status, session_scope
from ..industry import Industry, load_industry
from ..log import get_logger
from ..schema import Contact, HoursBlock, ImageRef, PriceItem, ServiceItem, SiteContent, Sourced, TeamMember, json_schema_for_llm, normalize_llm_output
from ..services.llm import LLM, make_llm
from ..validator import validate_content
from ..util import collapse_ws

log = get_logger("generation")

CLASS_DESCRIPTIONS = {
    "B": "Pkw-Führerschein, Schaltung oder Automatik",
    "B196": "Leichtkrafträder bis 125 ccm mit Pkw-Führerschein",
    "B197": "Pkw-Ausbildung mit Automatik, ohne Automatik-Beschränkung",
    "BE": "Pkw mit Anhänger",
    "A": "Motorrad ohne Leistungsbeschränkung",
    "A1": "Leichtkrafträder bis 125 ccm",
    "A2": "Motorräder bis 35 kW",
    "AM": "Roller und Mopeds bis 45 km/h",
    "L": "Land- und forstwirtschaftliche Zugmaschinen",
    "T": "Traktoren und selbstfahrende Arbeitsmaschinen",
    "C": "Lkw über 3,5 t",
    "C1": "Lkw bis 7,5 t",
    "CE": "Lkw mit Anhänger",
    "C1E": "Lkw bis 7,5 t mit Anhänger",
    "D": "Busse",
    "D1": "Kleinbusse",
}


def _first_paragraphs(text: str, min_len: int = 80, max_len: int = 600) -> str | None:
    """Take the first substantial paragraph(s) of the start/about page as 'about' copy."""
    chunks = [collapse_ws(c) for c in re.split(r"\n{1,}", text)]
    good = [c for c in chunks if len(c) >= min_len and not re.search(r"impressum|datenschutz|cookie|©|copyright|\d{5}\s", c, re.I)]
    out = ""
    for c in good:
        if len(out) + len(c) + 1 > max_len:
            break
        out = (out + " " + c).strip()
    return out or None


def compose_from_extracted(extracted: dict[str, Any], industry: Industry, company_name: str, city: str | None, imprint_source: str | None = None) -> SiteContent:
    """Deterministic composer: only copies facts that exist in the extracted candidates."""
    cand = extracted["candidates"]
    pages = extracted["pages"]
    start = next((p for p in pages if p["kind"] == "start"), pages[0] if pages else {"url": extracted["website"], "text": ""})
    about_page = next((p for p in pages if p["kind"] == "about"), None)
    src = imprint_source or start["url"]

    services = []
    for c in cand["classes"][:14]:
        key = c["name"].replace("Klasse ", "")
        price = None
        for pr in cand["prices"]:
            if re.search(rf"\bklasse\s*{re.escape(key)}\b", pr["label"], re.I):
                price = Sourced(value=pr["price"], source=pr["source"], snippet=pr["snippet"])
                break
        services.append(ServiceItem(name=Sourced(value=c["name"], source=c["source"], snippet=c["snippet"]), description=CLASS_DESCRIPTIONS.get(key), price=price))

    prices = [PriceItem(label=Sourced(value=p["label"], source=p["source"], snippet=p["snippet"]), price=Sourced(value=p["price"], source=p["source"], snippet=p["snippet"])) for p in cand["prices"][:12]]

    blocks: dict[str, list[Sourced]] = {}
    for h in cand["hours"]:
        blocks.setdefault(h["label"], []).append(Sourced(value=h["entry"], source=h["source"], snippet=h["snippet"]))
    hours = [HoursBlock(label=label[:60], entries=entries[:7]) for label, entries in list(blocks.items())[:4]]

    team = [TeamMember(name=Sourced(value=t["name"], source=t["source"], snippet=t["snippet"]), role=t["role"][:80] or None) for t in cand["team"][:8]]

    phone = cand["phones"][0] if cand["phones"] else None
    email = cand["emails"][0] if cand["emails"] else None
    address = cand["addresses"][0] if cand["addresses"] else None
    contact = Contact(
        phone=Sourced(value=phone["value"], source=phone["source"]) if phone else None,
        email=Sourced(value=email["value"], source=email["source"]) if email else None,
        address=Sourced(value=address["value"], source=address["source"], snippet=address.get("snippet")) if address else None,
    )

    images = [ImageRef(url=i["url"], alt=i["alt"][:120], role=("hero" if i.get("role") == "gallery" and i.get("width", 0) >= 1200 else i["role"])) for i in cand["images"][:6]]

    highlights: list[str] = []
    if services:
        names = [s.name.value.replace("Klasse ", "") for s in services]
        joined = "Klassen " + ", ".join(names)
        highlights.append(joined if len(joined) <= 70 else "Klassen " + ", ".join(names[:5]) + " u. a.")
    if hours:
        highlights.append("Feste Theorie- und Bürozeiten")
    if any(re.search(r"intensiv|ferienkurs", p["text"], re.I) for p in pages):
        highlights.append("Intensivkurse möglich")
    if any(re.search(r"automatik", p["text"], re.I) for p in pages):
        highlights.append("Ausbildung mit Automatik")
    if any(re.search(r"\bbf\s?17|begleitetes fahren", p["text"], re.I) for p in pages):
        highlights.append("Begleitetes Fahren ab 17")
    if any(re.search(r"erste[- ]hilfe", p["text"], re.I) for p in pages):
        highlights.append("Erste-Hilfe-Kurs vor Ort")

    city_part = f" in {city}" if city else ""
    tagline = f"Ihre {industry.label}{city_part}"
    hero_text = f"{company_name}{city_part}. Rufen Sie an oder schreiben Sie uns, wir beraten Sie gern zu Ihrer Fahrausbildung."
    about = _first_paragraphs(about_page["text"]) if about_page else None
    if not about:
        about = _first_paragraphs(start["text"])

    return SiteContent(
        industry=industry.name,
        company_name=Sourced(value=company_name, source=src),
        city=city,
        tagline=tagline[:90],
        hero_text=hero_text[:220],
        cta_primary="Jetzt anrufen" if phone else "Kontakt aufnehmen",
        highlights=[h[:70] for h in highlights[:4]],
        about=about,
        services=services,
        prices=prices,
        hours=hours,
        team=team,
        contact=contact,
        images=images,
    )


SYSTEM_PROMPT = """Du befüllst ein striktes JSON-Schema für eine neue One-Pager-Website eines lokalen Betriebs in Deutschland.
Du erhältst die extrahierten Texte der alten Website plus vorab gefundene Kandidaten (mit Quell-URL).

Unverhandelbare Regeln:
1. Verwende ausschließlich Fakten, die wörtlich in den Quelldaten stehen. Keine erfundenen Preise, Zeiten, Namen,
   Klassen, Telefonnummern, Bewertungen, Auszeichnungen, Erfolgsquoten, Zitate oder Gründungsjahre.
2. Jedes Faktenfeld (Sourced) trägt die Quell-URL und das exakte Quell-Snippet. Werte wörtlich übernehmen
   (Preise wie geschrieben, Zeiten wie geschrieben).
3. Fehlt eine Information, schreibe einen leeren Text "" (bei Fakten: value, source und snippet jeweils "") bzw. lass die Liste leer. Erfinde nie einen Platzhalter. Die Sektion wird dann ausgeblendet.
4. Werbetexte (tagline, hero_text, about, highlights, description) dürfen umformuliert werden, aber ohne neue
   Behauptungen, ohne Zahlen, die nicht in den Quellen stehen, ohne Superlative. Sie-Form, freundlich, klar, deutsch.
5. images: nur URLs aus der Kandidatenliste.
6. company_name: der offizielle Name aus dem Impressum.
"""


def _user_prompt(extracted: dict, industry: Industry, company_name: str, city: str | None) -> str:
    cand = json.dumps(extracted["candidates"], ensure_ascii=False)
    pages = "\n\n".join(f"=== {p['kind'].upper()} {p['url']}\n{p['text'][:6000]}" for p in extracted["pages"])
    return f"""Branche: {industry.label}. Firmenname laut Impressum: {company_name}. Stadt: {city or 'unbekannt'}.
Branchenhinweise: {industry.prompt_hints}

KANDIDATEN (bereits extrahiert, mit Quelle):
{cand}

QUELLTEXTE DER ALTEN WEBSITE:
{pages[:40000]}
"""


def generate_with_llm(llm: LLM, extracted: dict, industry: Industry, company_name: str, city: str | None) -> tuple[SiteContent, list[str]]:
    schema = json_schema_for_llm()
    user = _user_prompt(extracted, industry, company_name, city)
    last_error = ""
    for attempt in range(2):
        prompt = user if not last_error else user + f"\n\nDer vorherige Versuch war ungültig: {last_error}\nBitte korrigieren."
        raw = llm.complete_json(SYSTEM_PROMPT, prompt, schema)
        raw["industry"] = industry.name
        raw.pop("hero_image", None)
        try:
            content = SiteContent.model_validate(normalize_llm_output(raw))
        except ValidationError as e:
            last_error = str(e)[:800]
            log.warning("llm output failed schema", attempt=attempt, err=last_error[:200])
            continue
        result = validate_content(content, extracted["source_text"])
        if result.ok or attempt == 1:
            return content, result.warnings
        last_error = "; ".join(result.warnings[:5])
        log.info("llm output has validator warnings, retrying", n=len(result.warnings))
    raise RuntimeError(f"LLM output invalid: {last_error}")


def assign_hero_image(content: SiteContent, industry: Industry, seed: int) -> SiteContent:
    own = [i for i in content.images if i.role in ("hero", "gallery")]
    if own:
        content.hero_image = own[0].url
    elif industry.hero_images:
        content.hero_image = f"/industry-images/{industry.name}/{industry.hero_images[seed % len(industry.hero_images)]}"
    return content


def run(limit: int | None = None, costs: CostTracker | None = None, llm: LLM | None = None, use_llm: bool = True) -> dict:
    s = get_settings()
    industry = load_industry()
    costs = costs or CostTracker()
    llm = llm or (make_llm(costs) if use_llm else None)
    if llm is None:
        log.warning("ANTHROPIC_API_KEY fehlt – Inhalte werden regelbasiert zusammengesetzt (Mock-Generierung).")
    stats = {"generated": 0, "pending_review": 0, "auto_approved": 0, "failed": 0, "with_warnings": 0}
    with session_scope() as session:
        ids = [l.id for l in leads_in_status(session, LeadStatus.EXTRACTED, limit, industry.name)]
    for lead_id in ids:
        with session_scope() as session:
            lead = session.get(Lead, lead_id)
            company = lead.company_name or lead.places_name or lead.domain
            imprint = next((p["url"] for p in lead.extracted["pages"] if p["kind"] == "imprint"), None)
            warnings: list[str] = []
            content: SiteContent | None = None
            if llm is not None:
                try:
                    content, warnings = generate_with_llm(llm, lead.extracted, industry, company, lead.city)
                except BudgetExceeded as e:
                    log.warning(str(e))
                    llm = None
                except Exception as e:
                    log.error("llm generation failed, falling back to composer", lead=lead_id, err=str(e))
                    warnings = [f"LLM-Generierung fehlgeschlagen ({str(e)[:120]}), regelbasierter Fallback."]
            if content is None:
                try:
                    content = compose_from_extracted(lead.extracted, industry, company, lead.city, imprint)
                except Exception as e:
                    log.error("composer failed", lead=lead_id, err=str(e))
                    stats["failed"] += 1
                    continue
                warnings += validate_content(content, lead.extracted["source_text"]).warnings
            content = assign_hero_image(content, industry, lead_id)
            lead.generated = content.model_dump(mode="json")
            lead.validator_warnings = warnings
            lead.transition(LeadStatus.GENERATED, "llm" if llm else "composer", session)
            stats["generated"] += 1
            if warnings:
                stats["with_warnings"] += 1
            if s.AUTO_APPROVE and not warnings:
                lead.transition(LeadStatus.APPROVED, "auto-approve", session)
                stats["auto_approved"] += 1
            else:
                lead.transition(LeadStatus.PENDING_REVIEW, None, session)
                stats["pending_review"] += 1
            log.info("generated", lead=lead_id, sections=content.visible_sections(), warnings=len(warnings))
    log.info("generation done", **stats)
    return stats
