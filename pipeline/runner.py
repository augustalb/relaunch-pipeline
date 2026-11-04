"""Stage orchestration: `pipeline run --stage all` executes the chain in order."""

from __future__ import annotations

from datetime import datetime

from .costs import CostTracker
from .db import RunLog, session_scope, utcnow
from .log import get_logger
from .stages import contact, discovery, extraction, generation, housekeeping, preview, scoring, screenshots, sending, sync

log = get_logger("runner")

STAGES = ["housekeeping", "sync", "discovery", "scoring", "contact", "extraction", "generation", "preview", "screenshots", "sending", "report"]


def run_stage(name: str, limit: int | None, costs: CostTracker, *, deploy: bool = True, force_window: bool = False) -> dict:
    if name == "housekeeping":
        return housekeeping.run()
    if name == "sync":
        return sync.run()
    if name == "discovery":
        return discovery.run(limit, costs=costs)
    if name == "scoring":
        return scoring.run(limit, costs=costs)
    if name == "contact":
        return contact.run(limit, costs=costs)
    if name == "extraction":
        return extraction.run(limit)
    if name == "generation":
        return generation.run(limit, costs=costs)
    if name == "preview":
        return preview.run(limit, deploy=deploy)
    if name == "screenshots":
        return screenshots.run(limit)
    if name == "sending":
        return sending.run(limit, force_window=force_window)
    if name == "report":
        from .report import build_report, format_report, send_report_email

        data = build_report()
        text = format_report(data)
        print(text)
        data["emailed"] = send_report_email(text)
        return data
    raise ValueError(f"unknown stage {name}")


def run_all(stage: str = "all", limit: int | None = None, deploy: bool = True, force_window: bool = False) -> dict:
    costs = CostTracker()
    names = STAGES if stage == "all" else [stage]
    summary: dict[str, dict] = {}
    started = utcnow()
    for name in names:
        log.info(f"--- stage {name} ---")
        try:
            summary[name] = run_stage(name, limit, costs, deploy=deploy, force_window=force_window)
        except Exception as e:  # one failing stage must not kill the daily run
            log.error(f"stage {name} failed", exc_info=True, err=str(e))
            summary[name] = {"error": str(e)}
    summary["costs"] = costs.summary()
    with session_scope() as s:
        s.add(RunLog(run_id=costs.run_id, started_at=started, finished_at=utcnow(), stage=stage, summary=summary))
    return summary


_ = datetime
