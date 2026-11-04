"""Render the industry's e-mail templates for a lead."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .config import get_settings
from .db import Lead
from .industry import Industry
from .util import stable_variant

URL_RE = re.compile(r"https?://\S+")


@dataclass
class RenderedEmail:
    step: int
    subject: str
    body: str
    warnings: list[str]


def _parse_template(raw: str) -> tuple[str, list[str]]:
    lines = raw.strip().splitlines()
    subject = ""
    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        lines = lines[1:]
    body = "\n".join(lines)
    variants = [v.strip() for v in body.split("---variant---") if v.strip()]
    return subject, variants or [body.strip()]


def variables_for(lead: Lead) -> dict[str, str]:
    s = get_settings()
    findings = list(lead.findings or [])
    while len(findings) < 3:
        findings.append("")
    return {
        "anrede": lead.owner_salutation or "Guten Tag",
        "firma": lead.company_name or lead.places_name or lead.domain or "",
        "stadt": lead.city or "",
        "befund_1": findings[0],
        "befund_2": findings[1],
        "befund_3": findings[2],
        "preview_url": lead.preview_url or f"{s.preview_base_url}/{lead.preview_path or ''}",
        "sender_name": s.SENDER_NAME,
        "sender_title": s.SENDER_TITLE,
        "sender_address": s.SENDER_ADDRESS,
        "sender_phone": s.SENDER_PHONE,
    }


def render(template_name: str, industry: Industry, lead: Lead, step: int, variables: dict[str, str] | None = None) -> RenderedEmail:
    raw = industry.email_template(template_name)
    subject_t, variants = _parse_template(raw)
    variant = variants[stable_variant(f"{lead.id}:{template_name}", len(variants))]
    vars_ = variables or variables_for(lead)
    body = variant.format_map(_Safe(vars_))
    footer_file = industry.email_dir / "footer.md"
    if footer_file.exists():
        body = body.rstrip() + "\n\n" + footer_file.read_text(encoding="utf-8").strip().format_map(_Safe(vars_))
    body = re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"
    subject = subject_t.format_map(_Safe(vars_))
    return RenderedEmail(step=step, subject=subject, body=body, warnings=check_email(body))


def check_email(body: str) -> list[str]:
    w = []
    main = body.split("\n--\n", 1)[0]
    words = len(re.findall(r"\S+", main))
    if words > 120:
        w.append(f"E-Mail hat {words} Wörter (Ziel: unter 120).")
    links = URL_RE.findall(body)
    if len(links) != 1:
        w.append(f"E-Mail enthält {len(links)} Links (Ziel: genau 1).")
    if "{" in body and "}" in body:
        w.append("E-Mail enthält nicht ersetzte Platzhalter.")
    return w


def render_sequence(industry: Industry, lead: Lead) -> list[RenderedEmail]:
    return [
        render("initial", industry, lead, 1),
        render("followup_1", industry, lead, 2),
        render("followup_2", industry, lead, 3),
    ]


class _Safe(dict):
    def __missing__(self, key):
        return "{" + key + "}"
