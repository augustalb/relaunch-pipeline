from sqlalchemy import select

from pipeline.db import Lead, LeadStatus, session_scope
from pipeline.stages import redo


def test_reset_pending_moves_back_to_qualified():
    with session_scope() as s:
        lead = Lead(industry="fahrschulen", place_id="p1", status=LeadStatus.PENDING_REVIEW.value, owner_name="Weitere Informationen",
                    generated={"x": 1}, email_body="alt", preview_path="fs-abc123")
        other = Lead(industry="fahrschulen", place_id="p2", status=LeadStatus.SENT.value, email_body="gesendet")
        s.add_all([lead, other])
    assert redo.reset_pending() == {"reset": 1}
    with session_scope() as s:
        a = s.scalars(select(Lead).where(Lead.place_id == "p1")).one()
        b = s.scalars(select(Lead).where(Lead.place_id == "p2")).one()
        assert a.status == LeadStatus.QUALIFIED.value
        assert a.owner_name is None and a.generated is None and a.email_body is None
        assert a.preview_path is None  # rebuilt from the corrected name; never sent, so never shared
        assert b.status == LeadStatus.SENT.value and b.email_body == "gesendet"
