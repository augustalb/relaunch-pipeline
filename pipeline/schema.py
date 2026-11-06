"""Strict content schema for generated preview websites.

The LLM never writes HTML. It fills this schema; the Astro template renders it.
Every *fact* (names, prices, times, phone numbers, licence classes) is a
`Sourced` value that carries the URL and the snippet it came from. Marketing
copy (tagline, about, highlights) may be rephrased but must not add claims –
that is enforced by `pipeline.validator`.
"""

from __future__ import annotations

import types
from typing import Literal, Union, get_args, get_origin

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
    # Structured outputs reject length/size/number constraints and defaults (400 Bad Request) and
    # schemas with many optional or nullable fields ("Schema is too complex"). So the LLM gets a
    # schema where every field is required and never null; "missing" is "" or an empty list.
    # normalize_llm_output() turns those back into None before validating against SiteContent,
    # which still enforces every constraint.
    return _all_required(_strip_unsupported(schema))


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


def _all_required(node):
    if isinstance(node, dict):
        if "anyOf" in node:
            options = [o for o in node["anyOf"] if o.get("type") != "null"]
            if len(options) == 1:
                merged = {k: v for k, v in node.items() if k != "anyOf"}
                merged.update(options[0])
                return _all_required(merged)
        out = {k: _all_required(v) for k, v in node.items()}
        if out.get("type") == "object" and "properties" in out:
            out["required"] = list(out["properties"].keys())
        return out
    if isinstance(node, list):
        return [_all_required(v) for v in node]
    return node


def _unwrap(annotation):
    """Return (inner_type, nullable) for `X | None` / Optional[X]."""
    if get_origin(annotation) in (Union, types.UnionType):
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0], True
    return annotation, False


def _is_empty(value) -> bool:
    return value == "" or (isinstance(value, dict) and value.get("value", None) == "")


def _normalize(model: type[BaseModel], data):
    if not isinstance(data, dict):
        return data
    for name, field in model.model_fields.items():
        if name not in data:
            continue
        inner, nullable = _unwrap(field.annotation)
        value = data[name]
        if nullable and _is_empty(value):
            data[name] = None
            continue
        if isinstance(inner, type) and issubclass(inner, BaseModel):
            data[name] = _normalize(inner, value)
        elif get_origin(inner) is list and isinstance(value, list):
            (item_type,) = get_args(inner) or (None,)
            items = [v for v in value if not _is_empty(v)]  # drop empty facts the LLM used as placeholders
            if isinstance(item_type, type) and issubclass(item_type, BaseModel):
                items = [_normalize(item_type, v) for v in items]
            data[name] = items
    if model is Sourced and data.get("snippet") == "":
        data["snippet"] = None
    return data


def normalize_llm_output(raw: dict) -> dict:
    """Map the LLM's "" / empty placeholders back to None so SiteContent can validate them."""
    return _normalize(SiteContent, dict(raw))
