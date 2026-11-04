"""Stage 7 – Playwright screenshots (mobile) of the old site and the new preview, for the review UI."""

from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path

from ..config import PROJECT_ROOT, get_settings
from ..db import Lead, LeadStatus, session_scope
from ..log import get_logger

log = get_logger("screenshots")

MOBILE = {"width": 390, "height": 844, "device_scale_factor": 2, "is_mobile": True, "has_touch": True}


def screenshots_dir() -> Path:
    d = PROJECT_ROOT / "screenshots"
    d.mkdir(exist_ok=True)
    return d


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):  # noqa: D401
        pass


class StaticServer:
    """Serve a directory on a free localhost port in a background thread."""

    def __init__(self, directory: Path):
        self.directory = directory
        handler = lambda *a, **k: _Quiet(*a, directory=str(directory), **k)  # noqa: E731
        socketserver.TCPServer.allow_reuse_address = True
        self.httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()


def capture(url: str, out: Path, full_page: bool = True, timeout_ms: int = 30000) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.warning("Playwright nicht installiert – Screenshots übersprungen (pip install playwright && playwright install chromium).")
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            ctx = browser.new_context(viewport={"width": MOBILE["width"], "height": MOBILE["height"]}, device_scale_factor=MOBILE["device_scale_factor"], is_mobile=True, has_touch=True, locale="de-DE")
            page = ctx.new_page()
            page.goto(url, wait_until="load", timeout=timeout_ms)
            page.wait_for_timeout(800)
            page.screenshot(path=str(out), full_page=full_page)
            browser.close()
        return True
    except Exception as e:
        log.warning("screenshot failed", url=url, err=str(e)[:200])
        return False


def run(limit: int | None = None, dist_dir: Path | None = None) -> dict:
    s = get_settings()
    dist = dist_dir or (s.SITE_DIR / "dist")
    stats = {"before": 0, "after": 0}
    out = screenshots_dir()
    with session_scope() as session:
        from sqlalchemy import select

        leads = list(session.scalars(select(Lead).where(Lead.status.in_([LeadStatus.PENDING_REVIEW.value, LeadStatus.APPROVED.value]), Lead.preview_path.is_not(None)).order_by(Lead.id).limit(limit or 1000)))
        todo = [(l.id, l.website, l.preview_path, l.screenshot_before, l.screenshot_after) for l in leads]
    if not todo:
        return stats
    server = StaticServer(dist) if dist.exists() else None
    ctx = server if server else _Null()
    with ctx:
        for lead_id, website, slug, before, after in todo:
            if not before or not Path(before).exists():
                dst = out / f"{lead_id}-before.png"
                if capture(website, dst, full_page=False):
                    before = str(dst)
                    stats["before"] += 1
            if server and (not after or not Path(after).exists()):
                dst = out / f"{lead_id}-after.png"
                if capture(f"{server.url}/{slug}/", dst, full_page=False):
                    after = str(dst)
                    stats["after"] += 1
            with session_scope() as session:
                lead = session.get(Lead, lead_id)
                lead.screenshot_before, lead.screenshot_after = before, after
    log.info("screenshots done", **stats)
    return stats


class _Null:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False
