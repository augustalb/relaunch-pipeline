"""`pipeline demo` – the whole chain offline against the HTML fixtures in `fixtures/sites/`."""

from __future__ import annotations

import os
from pathlib import Path

from .config import PROJECT_ROOT, get_settings, reset_settings_cache
from .costs import CostTracker
from .db import Base, get_engine, reset_engine
from .log import get_logger
from .services.pagespeed import MockPageSpeedClient
from .services.places import MockPlacesClient
from .services.sender import DryRunSender
from .stages import contact, discovery, extraction, generation, preview, scoring, screenshots, sending, sync
from .stages.screenshots import StaticServer

log = get_logger("demo")

FIXTURE_CITIES = ["Köln", "Düsseldorf", "Dortmund", "Essen", "Bochum", "Wuppertal", "Bonn", "Münster"]


def run_demo(reset: bool = True, screenshots: bool = True, build: bool = True, limit: int | None = None, db_path: Path | None = None) -> dict:
    """Runs discovery(mock) → scoring(mock PSI) → contact → extraction → generation → preview build →
    screenshots → auto-approve clean leads → dry-run sending. Returns a stage summary."""
    os.environ.setdefault("PIPELINE_ENV_FILE", "/dev/null")  # ignore a real .env: the demo never touches paid APIs
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path or PROJECT_ROOT / 'data' / 'demo.db'}"
    os.environ.setdefault("AUTO_APPROVE", "true")
    os.environ.setdefault("REQUIRE_VERIFIED_EMAIL", "false")
    os.environ.setdefault("SENDER_BACKEND", "dryrun")
    os.environ.setdefault("PREVIEW_DOMAIN", "preview.example.de")
    os.environ.setdefault("SENDER_NAME", "August Albrecht")
    reset_settings_cache()
    reset_engine()
    s = get_settings()
    if reset:
        engine = get_engine()
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        for f in (s.SITE_DIR / "src" / "data" / "previews").glob("*.json"):
            f.unlink()
    costs = CostTracker()
    summary: dict = {}
    with StaticServer(PROJECT_ROOT / "fixtures" / "sites") as fixtures:
        log.info("fixture server", url=fixtures.url)
        summary["discovery"] = discovery.run(limit, cities=FIXTURE_CITIES, costs=costs, client=MockPlacesClient(fixtures.url))
        summary["scoring"] = scoring.run(limit, costs=costs, psi_client=MockPageSpeedClient())
        summary["contact"] = contact.run(limit, costs=costs, offline=True)
        summary["extraction"] = extraction.run(limit)
        summary["generation"] = generation.run(limit, costs=costs)  # real LLM if ANTHROPIC_API_KEY is set, else composer
        summary["preview"] = preview.run(limit, deploy=False) if build else {"skipped": True}
        if screenshots and build:
            summary["screenshots"] = screenshots_stage()
        summary["sync"] = sync.run(DryRunSender())
        summary["sending"] = sending.run(limit, sender=DryRunSender(), force_window=True)
    from .report import build_report, format_report

    summary["report"] = format_report(build_report())
    log.info("demo finished")
    return summary


def screenshots_stage() -> dict:
    return screenshots.run()
