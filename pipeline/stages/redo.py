"""Re-run contact -> generation for leads still waiting in review.

Used after fixing contact extraction or generation: leads in `pending_review`
(never approved, never sent) go back to `qualified` and run through the
chain again. Preview slug and URL are kept, so links stay stable.
"""

from __future__ import annotations

from ..db import Lead, LeadStatus, leads_in_status, session_scope
from ..industry import load_industry
from ..log import get_logger

log = get_logger("redo")

_RESET_FIELDS = (
    "owner_name", "owner_salutation", "extracted", "generated", "validator_warnings",
    "email_subject", "email_body", "followup_1_body", "followup_2_body", "screenshot_before", "screenshot_after",
)


def reset_pending(limit: int | None = None) -> dict:
    industry = load_industry()
    n = 0
    with session_scope() as session:
        for lead in leads_in_status(session, LeadStatus.PENDING_REVIEW, limit, industry.name):
            for f in _RESET_FIELDS:
                setattr(lead, f, None)
            lead.transition(LeadStatus.QUALIFIED, "erneut verarbeiten (redo_review)", session)
            n += 1
    log.info("pending leads reset", count=n)
    return {"reset": n}
