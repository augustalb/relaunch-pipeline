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
    cmd = ["npx", "--yes", "wrangler@3", "pages", "deploy", str(dist_dir), "--project-name", project, "--branch", branch, "--commit-dirty=true"]
    log.info("deploying to Cloudflare Pages", project=project)
    try:
        subprocess.run(cmd, check=True, env=_env(), cwd=str(s.SITE_DIR), timeout=600)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        log.error("wrangler deploy failed", err=str(e))
        return False
    return True


def ensure_project(project: str) -> bool:
    """Create a Pages project if it does not exist (idempotent)."""
    s = get_settings()
    if not (s.CLOUDFLARE_API_TOKEN and s.CLOUDFLARE_ACCOUNT_ID) or not wrangler_available():
        return False
    try:
        subprocess.run(["npx", "--yes", "wrangler@3", "pages", "project", "create", project, "--production-branch", "main"], env=_env(), cwd=str(s.SITE_DIR), timeout=300, check=False)
    except subprocess.TimeoutExpired:
        return False
    return True
