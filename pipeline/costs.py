"""Per-run cost tracking and budget enforcement for paid APIs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select

from .config import get_settings
from .db import CostEntry, session_scope
from .log import get_logger

log = get_logger("costs")


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class CostTracker:
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    totals: dict[str, float] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)

    def record(self, service: str, eur: float, units: float = 1.0, note: str | None = None) -> None:
        self.totals[service] = self.totals.get(service, 0.0) + eur
        self.counts[service] = self.counts.get(service, 0) + 1
        with session_scope() as s:
            s.add(CostEntry(run_id=self.run_id, service=service, units=units, eur=eur, note=(note[:250] if note else note)))

    def check_requests(self, service: str, max_requests: int) -> None:
        if self.counts.get(service, 0) >= max_requests:
            raise BudgetExceeded(f"{service}: request limit {max_requests} per run reached")

    def check_eur(self, service: str, max_eur: float) -> None:
        if self.totals.get(service, 0.0) >= max_eur:
            raise BudgetExceeded(f"{service}: cost limit {max_eur:.2f} EUR per run reached")

    def summary(self) -> dict[str, float]:
        return {k: round(v, 4) for k, v in self.totals.items()}


def costs_since(days: int = 1) -> dict[str, float]:
    from datetime import datetime, timedelta, timezone

    since = datetime.now(timezone.utc) - timedelta(days=days)
    with session_scope() as s:
        rows = s.execute(
            select(CostEntry.service, func.sum(CostEntry.eur), func.count())
            .where(CostEntry.created_at >= since)
            .group_by(CostEntry.service)
        ).all()
    return {svc: {"eur": round(eur or 0.0, 4), "requests": n} for svc, eur, n in rows}


_ = get_settings  # keep import for type checkers
