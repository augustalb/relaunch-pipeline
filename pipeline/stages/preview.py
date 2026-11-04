"""Stage 6 – Preview build & deploy (Astro + Tailwind, one Cloudflare Pages project for all previews)."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from ..config import get_settings
from ..db import Lead, LeadStatus, leads_in_status, session_scope, utcnow
from ..industry import Industry, list_industries, load_industry
from ..log import get_logger
from ..services import cloudflare
from ..util import preview_slug

log = get_logger("preview")


def previews_dir() -> Path:
    d = get_settings().SITE_DIR / "src" / "data" / "previews"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sync_industry_assets() -> None:
    """Copy every industry's curated images into the site's public folder (templates are imported directly)."""
    s = get_settings()
    for name in list_industries():
        ind = load_industry(name)
        if ind.images_dir.exists():
            dest = s.SITE_DIR / "public" / "industry-images" / name
            dest.mkdir(parents=True, exist_ok=True)
            for img in ind.images_dir.iterdir():
                if img.is_file() and img.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".svg"}:
                    shutil.copyfile(img, dest / img.name)


def preview_file(lead: Lead, industry: Industry, mode: str = "preview") -> dict:
    s = get_settings()
    pages = (lead.extracted or {}).get("pages", [])
    imprint = next((p["url"] for p in pages if p["kind"] == "imprint"), None)
    privacy = next((p["url"] for p in pages if "datenschutz" in p["url"].lower() or "privacy" in p["url"].lower()), None)
    return {
        "meta": {
            "slug": lead.preview_path,
            "company": lead.display_name,
            "sender_name": s.SENDER_NAME,
            "brand_name": s.brand_name,
            "reply_to": s.REPLY_TO_EMAIL,
            "old_website": lead.website,
            "imprint_url": imprint,
            "privacy_url": privacy,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "mode": mode,
        },
        "content": lead.generated,
    }


def write_preview_json(lead: Lead, industry: Industry) -> Path:
    if not lead.preview_path:
        lead.preview_path = preview_slug(lead.display_name)
    path = previews_dir() / f"{lead.preview_path}.json"
    path.write_text(json.dumps(preview_file(lead, industry), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_all_active_previews() -> int:
    """Re-create JSON for every lead that should currently have a live preview (idempotent rebuild)."""
    industry_cache: dict[str, Industry] = {}
    live = [LeadStatus.APPROVED, LeadStatus.QUEUED, LeadStatus.SENT, LeadStatus.REPLIED, LeadStatus.WON, LeadStatus.PENDING_REVIEW, LeadStatus.GENERATED]
    n = 0
    d = previews_dir()
    for f in d.glob("*.json"):
        f.unlink()
    with session_scope() as session:
        for lead in session.scalars(select(Lead).where(Lead.status.in_([x.value for x in live]), Lead.generated.is_not(None))):
            ind = industry_cache.setdefault(lead.industry, load_industry(lead.industry))
            write_preview_json(lead, ind)
            n += 1
    return n


def npm_available() -> bool:
    return shutil.which("npm") is not None


def build_site(env_extra: dict[str, str] | None = None, out_dir: Path | None = None) -> Path | None:
    """Run `astro build`. Returns dist path or None when node/npm is missing."""
    import os

    s = get_settings()
    if not npm_available():
        log.warning("npm nicht gefunden – Preview-Build übersprungen (Node.js 20+ installieren).")
        return None
    sync_industry_assets()
    if not (s.SITE_DIR / "node_modules").exists():
        log.info("installing site dependencies (npm ci)")
        subprocess.run(["npm", "ci", "--no-audit", "--no-fund"], cwd=str(s.SITE_DIR), check=True, timeout=600)
    env = os.environ.copy()
    env["SITE_URL"] = s.preview_base_url
    env.update(env_extra or {})
    cmd = ["npx", "astro", "build"]
    if out_dir:
        cmd += ["--outDir", str(out_dir)]
    log.info("building previews", dir=str(s.SITE_DIR))
    subprocess.run(cmd, cwd=str(s.SITE_DIR), check=True, env=env, timeout=900, stdout=subprocess.DEVNULL)
    return out_dir or (s.SITE_DIR / "dist")


def run(limit: int | None = None, deploy: bool = True) -> dict:
    """Assign slugs/URLs to approved leads, rebuild the whole site, deploy."""
    s = get_settings()
    industry = load_industry()
    stats = {"new_previews": 0, "built": 0, "deployed": False}
    with session_scope() as session:
        for lead in leads_in_status(session, LeadStatus.APPROVED, limit, industry.name) + leads_in_status(session, LeadStatus.PENDING_REVIEW, limit, industry.name):
            if not lead.preview_path:
                lead.preview_path = preview_slug(lead.display_name)
                lead.preview_url = f"{s.preview_base_url}/{lead.preview_path}/"
                stats["new_previews"] += 1
    stats["built"] = write_all_active_previews()
    dist = build_site()
    if dist and deploy:
        ok = cloudflare.deploy(dist)
        stats["deployed"] = ok
        if ok:
            with session_scope() as session:
                for lead in session.scalars(select(Lead).where(Lead.preview_path.is_not(None), Lead.status.in_([LeadStatus.APPROVED.value, LeadStatus.QUEUED.value]))):
                    lead.preview_deployed_at = utcnow()
    log.info("preview done", **stats)
    return stats
