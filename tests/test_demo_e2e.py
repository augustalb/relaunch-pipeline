"""End-to-end: the offline demo run against the fixtures, including the Astro build and screenshots
when node / Playwright are available (they are skipped gracefully otherwise)."""

import shutil
from email import message_from_bytes

import pytest
from sqlalchemy import select

from pipeline.db import Lead, LeadStatus, session_scope


@pytest.mark.timeout(900)
def test_demo_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTBOX_DIR", str(tmp_path / "outbox"))
    from pipeline.demo import run_demo

    have_node = shutil.which("npm") is not None
    summary = run_demo(reset=True, screenshots=have_node, build=have_node, db_path=tmp_path / "demo.db")

    d = summary["discovery"]
    assert d["new_leads"] == 8 and d["excluded_no_site"] == 2 and d["disqualified"] == 2 and d["dup_domain"] == 1
    assert summary["scoring"]["qualified"] == 7 and summary["scoring"]["disqualified"] == 1  # modern control site stays out
    assert summary["contact"]["contact_found"] == 7
    assert summary["extraction"]["extracted"] == 7
    assert summary["generation"]["generated"] == 7 and summary["generation"]["with_warnings"] == 0
    assert summary["sending"]["sent"] == 7

    with session_scope() as s:
        leads = list(s.scalars(select(Lead).where(Lead.status == LeadStatus.SENT.value)))
        assert len(leads) == 7
        for l in leads:
            assert l.email and l.preview_url and l.email_body and "{" not in l.email_body
            assert l.email_body.count("http") == 1  # exactly one link
            assert l.generated["company_name"]["value"]
            assert not l.validator_warnings
        by_name = {l.display_name: l for l in leads}
        assert by_name["Fahrschule Rote Ampel"].generated["prices"] == []  # no invented prices
        assert by_name["Fahrschule Rote Ampel"].owner_salutation == "Sehr geehrter Herr Berger"
        assert by_name["Fahrschule Müller"].owner_salutation == "Sehr geehrter Herr Müller"  # explicit "Herr" in imprint
        assert by_name["Fahrschule Drive-In Schmidt"].owner_salutation == "Sehr geehrte Frau Schmidt"  # first-name list
        assert by_name["Fahrschule Schwebe"].email == "info@fahrschule-schwebe.de"  # JS-only site rendered with Playwright
        modern = s.scalar(select(Lead).where(Lead.places_name == "Fahrschule Westfalen"))
        assert modern.status == LeadStatus.DISQUALIFIED.value

    emls = sorted((tmp_path / "outbox").glob("*.eml"))
    assert len(emls) == 21  # 7 leads x (initial + 2 follow-ups)
    msg = message_from_bytes(emls[0].read_bytes())
    assert msg["Reply-To"] == "auguyoga@gmail.com"
    assert "Kein Interesse?" in msg.get_payload(decode=True).decode()

    if have_node:
        assert summary["preview"]["built"] == 7
        from pipeline.config import get_settings

        assert (get_settings().SITE_DIR / "dist" / "robots.txt").read_text().strip().endswith("Disallow: /")
        assert summary["screenshots"]["after"] == 7
