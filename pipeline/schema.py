"""Strict content schema for generated preview websites.

The LLM never writes HTML. It fills this schema; the Astro template renders it.
Every *fact* (names, prices, times, phone numbers, licence classes) is a
`Sourced` value that carries the URL and the snippet it came from. Marketing
copy (tagline, about, highlights) may be rephrased but must not add claims –
that is enforced by `pipeline.validator`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Sourced(Strict):
    value: str = Field(..., min_length=1, description="The fact, verbatim or minimally normalised")
    source: str = Field(..., description="URL of the page the fact was taken from")
    snippet: str | None = Field(None, description="Exact text passage from the source containing the fact")


class ServiceItem(Strict):
    name: Sourced = Field(..., description="e.g. 'Klasse B' – must appear in the source")
    description: str | None = Field(None, max_length=240, description="Short description, rephrased, no new claims")
    price: Sourced | None = Field(None, description="Price exactly as written on the source, e.g. '49,00 €'")


class PriceItem(Strict):
    label: Sourced
    price: Sourced


class HoursBlock(Strict):
    label: str = Field(..., max_length=60, description="e.g. 'Bürozeiten' or 'Theorieunterricht'")
    entries: list[Sourced] = Field(..., min_length=1, description="e.g. 'Mo–Fr 15:00–18:00'")


class TeamMember(Strict):
    name: Sourced
    role: str | None = Field(None, max_length=80)


class Contact(Strict):
    phone: Sourced | None = None
    email: Sourced | None = None
    address: Sourced | None = None
    whatsapp: Sourced | None = None


class ImageRef(Strict):
    url: str = Field(..., description="Absolute URL on the business's own domain")
    alt: str = Field("", max_length=120)
    role: Literal["logo", "hero", "gallery"] = "gallery"


class SiteContent(Strict):
    industry: str
    company_name: Sourced
    city: str | None = None
    tagline: str = Field(..., max_length=90, description="Short headline, rephrased, no new claims")
    hero_text: str = Field(..., max_length=220)
    cta_primary: str = Field("Jetzt Kontakt aufnehmen", max_length=40)
    highlights: list[str] = Field(default_factory=list, max_length=4, description="Max 4 bullets, each <= 70 chars, derived from source")
    about: str | None = Field(None, max_length=700)
    services: list[ServiceItem] = Field(default_factory=list, max_length=14)
    prices: list[PriceItem] = Field(default_factory=list, max_length=20)
    price_note: str | None = Field(None, max_length=200)
    hours: list[HoursBlock] = Field(default_factory=list, max_length=4)
    team: list[TeamMember] = Field(default_factory=list, max_length=12)
    contact: Contact = Field(default_factory=Contact)
    images: list[ImageRef] = Field(default_factory=list, max_length=8)
    hero_image: str | None = Field(None, description="Filled by the pipeline: own image URL or curated stock file name")

    @field_validator("highlights")
    @classmethod
    def _short_highlights(cls, v: list[str]) -> list[str]:
        for h in v:
            if len(h) > 70:
                raise ValueError(f"highlight too long: {h!r}")
        return v

    def visible_sections(self) -> list[str]:
        """Sections with data. Everything else is hidden by the template."""
        out = ["hero"]
        if self.highlights:
            out.append("highlights")
        if self.services:
            out.append("services")
        if self.prices:
            out.append("prices")
        if self.hours:
            out.append("hours")
        if self.team:
            out.append("team")
        if self.about:
            out.append("about")
        if any([self.contact.phone, self.contact.email, self.contact.address]):
            out.append("contact")
        return out


def json_schema_for_llm() -> dict:
    """JSON schema handed to the LLM (structured outputs)."""
    schema = SiteContent.model_json_schema()
    # The pipeline fills hero_image itself.
    schema["properties"].pop("hero_image", None)
    if "hero_image" in schema.get("required", []):
        schema["required"].remove("hero_image")
    # Structured outputs reject length/size/number constraints and defaults (400 Bad Request).
    # They stay enforced: the response is validated against SiteContent afterwards.
    return _strip_unsupported(schema)


_UNSUPPORTED_KEYS = {
    "minLength", "maxLength", "pattern", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "multipleOf", "minItems", "maxItems", "uniqueItems", "default",
}


def _strip_unsupported(node):
    if isinstance(node, dict):
        out = {k: _strip_unsupported(v) for k, v in node.items() if k not in _UNSUPPORTED_KEYS}
        if out.get("type") == "object":
            out["additionalProperties"] = False
        return out
    if isinstance(node, list):
        return [_strip_unsupported(v) for v in node]
    return node
