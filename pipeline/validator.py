"""Hallucination validator.

Checks that every number, time, phone number and person/company name in the
generated `SiteContent` actually occurs in the extracted source text. Any
violation is returned as a human-readable warning; the review UI shows them
and `AUTO_APPROVE` never approves a lead with warnings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .schema import SiteContent, Sourced
from .util import collapse_ws

_DIGIT_RUN = re.compile(r"\d+")
_TIME = re.compile(r"\b\d{1,2}[:.]\d{2}\b")
_PHONE_CHARS = re.compile(r"[^\d+]")
_FORBIDDEN_CLAIMS = [
    r"\b\d{2,3}\s?%\s?(bestehens|erfolgs)",
    r"testsieger",
    r"ausgezeichnet",
    r"award",
    r"\bbeste fahrschule\b",
    r"\bnr\.?\s?1\b",
    r"\bseit \d{4}\b",
    r"\b\d+\s?(jahre|jahren)\s+erfahrung",
    r"\b\d+\.?\d*\s+(zufriedene|glückliche)\s+(kunden|fahrschüler)",
    r"\b(5|fünf)\s?sterne",
]


@dataclass
class ValidationResult:
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.warnings


def _norm(text: str) -> str:
    return collapse_ws(text).lower()


def _digits_only(s: str) -> str:
    return _PHONE_CHARS.sub("", s)


class SourceIndex:
    """Pre-computed views of the source corpus for fast membership tests."""

    def __init__(self, source_text: str):
        self.text = _norm(source_text)
        self.text_nospace = self.text.replace(" ", "")
        deob = re.sub(r"\s*(?:\[at\]|\(at\)|\{at\}|\[ät\]|\(ät\)|&#64;|\sat\s)\s*", "@", self.text)
        deob = re.sub(r"\s*(?:\[dot\]|\(dot\)|\[punkt\]|\(punkt\))\s*", ".", deob)
        self.text_deobfuscated = deob.replace(" ", "")
        self.digit_runs = set(_DIGIT_RUN.findall(self.text))
        self.digits_compact = _digits_only(self.text)

    def contains_phrase(self, phrase: str) -> bool:
        p = _norm(phrase)
        return bool(p) and (p in self.text or p.replace(" ", "") in self.text_nospace)

    def contains_number(self, run: str) -> bool:
        return run in self.digit_runs or run.lstrip("0") in {r.lstrip("0") for r in self.digit_runs if r}

    def contains_phone(self, phone: str) -> bool:
        d = _digits_only(phone).lstrip("+")
        if d.startswith("49"):
            d = "0" + d[2:]
        d_alt = d[1:] if d.startswith("0") else d
        return bool(d) and (d in self.digits_compact or (len(d_alt) >= 6 and d_alt in self.digits_compact))


def _check_numbers_in_text(idx: SourceIndex, text: str, where: str, out: list[str]) -> None:
    for run in _DIGIT_RUN.findall(text or ""):
        if not idx.contains_number(run):
            out.append(f"{where}: Zahl „{run}“ kommt in den Quelldaten nicht vor („{collapse_ws(text)[:80]}“).")
            return


def _check_sourced(idx: SourceIndex, s: Sourced | None, where: str, out: list[str], *, kind: str = "text") -> None:
    if s is None:
        return
    if kind == "phone":
        if not idx.contains_phone(s.value):
            out.append(f"{where}: Telefonnummer „{s.value}“ nicht in den Quelldaten gefunden.")
        return
    if kind == "name":
        if not idx.contains_phrase(s.value):
            out.append(f"{where}: Name „{s.value}“ nicht in den Quelldaten gefunden.")
        return
    # generic: all digit runs must exist and, for short values, the phrase itself
    for run in _DIGIT_RUN.findall(s.value):
        if not idx.contains_number(run):
            out.append(f"{where}: Zahl „{run}“ aus „{s.value}“ nicht in den Quelldaten gefunden.")
            return
    for t in _TIME.findall(s.value):
        if not idx.contains_phrase(t) and not idx.contains_phrase(t.replace(".", ":")):
            out.append(f"{where}: Uhrzeit „{t}“ nicht in den Quelldaten gefunden.")
            return
    if len(s.value) <= 40 and not _DIGIT_RUN.search(s.value) and not idx.contains_phrase(s.value):
        # short label-like values (e.g. "Klasse B", "Intensivkurs") must be literally present
        out.append(f"{where}: „{s.value}“ nicht wörtlich in den Quelldaten gefunden.")


def validate_content(content: SiteContent, source_text: str) -> ValidationResult:
    idx = SourceIndex(source_text)
    w: list[str] = []

    _check_sourced(idx, content.company_name, "Firmenname", w, kind="name")
    for i, svc in enumerate(content.services, 1):
        _check_sourced(idx, svc.name, f"Leistung {i}", w)
        _check_sourced(idx, svc.price, f"Preis Leistung {i}", w)
        _check_numbers_in_text(idx, svc.description or "", f"Beschreibung Leistung {i}", w)
    for i, p in enumerate(content.prices, 1):
        _check_sourced(idx, p.label, f"Preisposition {i}", w)
        _check_sourced(idx, p.price, f"Preis {i}", w)
    for block in content.hours:
        for e in block.entries:
            _check_sourced(idx, e, f"Zeiten „{block.label}“", w)
    for i, m in enumerate(content.team, 1):
        _check_sourced(idx, m.name, f"Teammitglied {i}", w, kind="name")
    _check_sourced(idx, content.contact.phone, "Telefon", w, kind="phone")
    _check_sourced(idx, content.contact.whatsapp, "WhatsApp", w, kind="phone")
    if content.contact.email and not (idx.contains_phrase(content.contact.email.value) or content.contact.email.value.lower() in idx.text_deobfuscated):
        w.append(f"E-Mail „{content.contact.email.value}“ nicht in den Quelldaten gefunden.")
    if content.contact.address:
        _check_numbers_in_text(idx, content.contact.address.value, "Adresse", w)

    for where, text in [("Slogan", content.tagline), ("Hero-Text", content.hero_text), ("Über uns", content.about or ""), ("Preis-Hinweis", content.price_note or "")] + [
        (f"Highlight {i}", h) for i, h in enumerate(content.highlights, 1)
    ]:
        _check_numbers_in_text(idx, text, where, w)
        low = (text or "").lower()
        for pat in _FORBIDDEN_CLAIMS:
            m = re.search(pat, low)
            if m and not idx.contains_phrase(m.group(0)):
                w.append(f"{where}: mögliche erfundene Behauptung „{m.group(0)}“.")
                break

    return ValidationResult(warnings=w)
