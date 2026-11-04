"""Industry packs.

An industry is a folder under `industries/<name>/` containing:

    industry.yaml        search terms, labels, scoring tweaks, prompt hints
    schema.json          extra JSON-Schema constraints (optional, merged into the base schema)
    email/initial.md     first e-mail (variants separated by a line `---variant---`)
    email/followup_1.md  follow-up ~day 3-4
    email/followup_2.md  follow-up ~day 7-8
    site/Template.astro  the Astro component rendering a preview for this industry
    site/images/         curated royalty-free hero images + LICENSES.md

Adding a new industry = adding a folder. No code changes required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from .config import PROJECT_ROOT, get_settings


@dataclass
class Industry:
    name: str
    path: Path
    label: str
    search_terms: list[str]
    service_label: str
    service_singular: str
    page_keywords: dict[str, list[str]]
    scoring: dict
    prompt_hints: str
    sections: list[str]
    hero_images: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    @property
    def email_dir(self) -> Path:
        return self.path / "email"

    @property
    def template_file(self) -> Path:
        return self.path / "site" / "Template.astro"

    @property
    def images_dir(self) -> Path:
        return self.path / "site" / "images"

    def email_template(self, name: str) -> str:
        return (self.email_dir / f"{name}.md").read_text(encoding="utf-8")


def list_industries() -> list[str]:
    base = PROJECT_ROOT / "industries"
    return sorted(p.name for p in base.iterdir() if (p / "industry.yaml").exists())


@lru_cache
def load_industry(name: str | None = None) -> Industry:
    name = name or get_settings().INDUSTRY
    path = PROJECT_ROOT / "industries" / name
    cfg_file = path / "industry.yaml"
    if not cfg_file.exists():
        raise FileNotFoundError(f"industry pack not found: {cfg_file}")
    cfg = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
    images_dir = path / "site" / "images"
    hero_images = sorted(p.name for p in images_dir.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".svg"}) if images_dir.exists() else []
    return Industry(
        name=name,
        path=path,
        label=cfg.get("label", name),
        search_terms=cfg.get("search_terms", [name]),
        service_label=cfg.get("service_label", "Leistungen"),
        service_singular=cfg.get("service_singular", "Leistung"),
        page_keywords=cfg.get("page_keywords", {}),
        scoring=cfg.get("scoring", {}),
        prompt_hints=cfg.get("prompt_hints", ""),
        sections=cfg.get("sections", ["hero", "services", "about", "prices", "hours", "team", "contact"]),
        hero_images=hero_images,
        extra={k: v for k, v in cfg.items() if k not in {"label", "search_terms", "service_label", "service_singular", "page_keywords", "scoring", "prompt_hints", "sections"}},
    )
