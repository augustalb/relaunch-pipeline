from pipeline.db import Lead, LeadStatus, session_scope
from pipeline.services import blocklist as bl
from pipeline.stages.sync import apply_event
from pipeline.services.sender import InboundEvent
from datetime import datetime, timezone


def test_block_and_match_email_and_domain():
    with session_scope() as s:
        assert bl.add(s, "Info@Fahrschule-A.de", "test")
        assert not bl.add(s, "info@fahrschule-a.de", "dup")
        assert bl.is_blocked(s, email="INFO@fahrschule-a.de")
        assert not bl.is_blocked(s, email="other@fahrschule-a.de")  # only the address was blocked
        bl.block_contact(s, "chef@fahrschule-b.de", "www.fahrschule-b.de", "unsubscribe")
        assert bl.is_blocked(s, email="irgendwer@fahrschule-b.de")
        assert bl.is_blocked(s, domain="https://fahrschule-b.de/x")
        assert not bl.is_blocked(s, email="x@fahrschule-c.de")


def test_negative_reply_blocks_and_marks_lost():
    with session_scope() as s:
        lead = Lead(industry="fahrschulen", place_id="p1", website="https://x.de", domain="x.de", email="info@x.de", status=LeadStatus.SENT.value, sent_at=datetime.now(timezone.utc))
        s.add(lead)
        s.flush()
        out = apply_event(s, InboundEvent(email="info@x.de", kind="replied", at=datetime.now(timezone.utc), excerpt="Kein Interesse, bitte nicht mehr anschreiben."))
        assert out == "lost"
        assert lead.status == LeadStatus.LOST.value
        assert bl.is_blocked(s, email="info@x.de") and bl.is_blocked(s, domain="x.de")


def test_positive_reply_does_not_block():
    with session_scope() as s:
        lead = Lead(industry="fahrschulen", place_id="p2", website="https://y.de", domain="y.de", email="info@y.de", status=LeadStatus.SENT.value, sent_at=datetime.now(timezone.utc))
        s.add(lead)
        s.flush()
        assert apply_event(s, InboundEvent(email="info@y.de", kind="replied", at=datetime.now(timezone.utc), excerpt="Klingt interessant, rufen Sie mich an.")) == "replied"
        assert lead.status == LeadStatus.REPLIED.value
        assert not bl.is_blocked(s, email="info@y.de")


def test_bounce_and_unsubscribe():
    with session_scope() as s:
        a = Lead(industry="fahrschulen", place_id="p3", website="https://a.de", domain="a.de", email="info@a.de", status=LeadStatus.SENT.value, sent_at=datetime.now(timezone.utc))
        b = Lead(industry="fahrschulen", place_id="p4", website="https://b.de", domain="b.de", email="info@b.de", status=LeadStatus.SENT.value, sent_at=datetime.now(timezone.utc))
        s.add_all([a, b])
        s.flush()
        assert apply_event(s, InboundEvent(email="info@a.de", kind="bounced", at=datetime.now(timezone.utc))) == "bounced"
        assert apply_event(s, InboundEvent(email="info@b.de", kind="unsubscribed", at=datetime.now(timezone.utc))) == "unsubscribed"
        assert a.status == "bounced" and b.status == "unsubscribed"
        assert bl.is_blocked(s, email="info@b.de")


def test_sending_skips_blocked(tmp_path):
    from pipeline.services.sender import DryRunSender
    from pipeline.stages import sending

    with session_scope() as s:
        lead = Lead(industry="fahrschulen", place_id="p5", website="https://c.de", domain="c.de", email="info@c.de", company_name="Fahrschule C", status=LeadStatus.APPROVED.value, findings=["Befund."], preview_url="https://p.de/x/")
        s.add(lead)
        bl.add(s, "c.de", "manual")
    stats = sending.run(sender=DryRunSender(tmp_path), force_window=True)
    assert stats["blocked"] == 1 and stats["sent"] == 0
    with session_scope() as s:
        assert s.get(Lead, 1).status == LeadStatus.REJECTED.value
