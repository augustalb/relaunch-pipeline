"""Cloudflare Pages deployment via `wrangler` (direct upload).

One Pages project hosts *all* previews under `{PREVIEW_DOMAIN}/{slug}`. Each
run rebuilds the Astro site from the JSON files currently on disk and
re-deploys the whole `dist/` folder, so removing a JSON file (expiry) removes
the preview with the next deploy.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from ..config import get_settings
from ..log import get_logger

log = get_logger("cloudflare")


def wrangler_available() -> bool:
    return shutil.which("npx") is not None


def _env() -> dict[str, str]:
    s = get_settings()
    env = os.environ.copy()
    env["CLOUDFLARE_API_TOKEN"] = s.CLOUDFLARE_API_TOKEN
    env["CLOUDFLARE_ACCOUNT_ID"] = s.CLOUDFLARE_ACCOUNT_ID
    return env


def deploy(dist_dir: Path, project: str | None = None, branch: str = "main") -> bool:
    """Deploy `dist_dir` to Cloudflare Pages. Returns False (and logs) when not configured."""
    s = get_settings()
    project = project or s.CLOUDFLARE_PAGES_PROJECT
    if not (s.CLOUDFLARE_API_TOKEN and s.CLOUDFLARE_ACCOUNT_ID):
        log.warning("Cloudflare not configured (CLOUDFLARE_API_TOKEN/CLOUDFLARE_ACCOUNT_ID) – skipping deploy; previews stay local in site/dist")
        return False
    if not wrangler_available():
        log.warning("npx not found – cannot run wrangler")
        return False
    if not ensure_project(project):
        log.error("Cloudflare Pages project missing and could not be created", project=project)
        return False
    cmd = ["npx", "--yes", "wrangler@3", "pages", "deploy", str(dist_dir), "--project-name", project, "--branch", branch, "--commit-dirty=true"]
    log.info("deploying to Cloudflare Pages", project=project)
    try:
        subprocess.run(cmd, check=True, env=_env(), cwd=str(s.SITE_DIR), timeout=600)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        log.error("wrangler deploy failed", err=str(e))
        return False
    return True


CF_API = "https://api.cloudflare.com/client/v4"


def ensure_project(project: str, client=None) -> bool:
    """Create the Pages project if it does not exist yet (idempotent, via the Cloudflare API)."""
    import httpx

    s = get_settings()
    if not (s.CLOUDFLARE_API_TOKEN and s.CLOUDFLARE_ACCOUNT_ID):
        return False
    own = client is None
    client = client or httpx.Client(timeout=30)
    headers = {"Authorization": f"Bearer {s.CLOUDFLARE_API_TOKEN}"}
    base = f"{CF_API}/accounts/{s.CLOUDFLARE_ACCOUNT_ID}/pages/projects"
    try:
        r = client.get(f"{base}/{project}", headers=headers)
        if r.status_code == 200:
            return True
        if r.status_code != 404:
            log.error("cloudflare project lookup failed", status=r.status_code, body=r.text[:200])
            return False
        r = client.post(base, headers=headers, json={"name": project, "production_branch": "main"})
        if r.status_code in (200, 201) and r.json().get("success"):
            log.info("created Cloudflare Pages project", project=project)
            return True
        log.error("cloudflare project create failed", status=r.status_code, body=r.text[:200])
        return False
    except httpx.HTTPError as e:
        log.error("cloudflare api error", err=str(e)[:200])
        return False
    finally:
        if own:
            client.close()
