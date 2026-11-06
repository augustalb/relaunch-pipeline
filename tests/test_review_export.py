from pipeline.db import Lead, LeadStatus, session_scope
from pipeline.review.export import export


def test_review_report_lists_pending_leads(tmp_path):
    shot = tmp_path / "1-before.png"
    shot.write_bytes(b"\x89PNG\r\n\x1a\n")
    with session_scope() as s:
        s.add(Lead(industry="fahrschulen", place_id="p1", status=LeadStatus.PENDING_REVIEW.value, company_name="Fahrschule Muster",
                   city="Bornheim", website="https://fs-muster.de/", email="info@fs-muster.de", score=48,
                   findings=["Ihre Website wird ohne HTTPS-Verschlüsselung ausgeliefert."], preview_path="fahrschule-muster-abc123",
                   screenshot_before=str(shot), score_details={"visual": {"outdated": 8, "mobile_usability": 3, "reasons": ["winzige Schrift"]}}))
        s.add(Lead(industry="fahrschulen", place_id="p2", status=LeadStatus.SENT.value, company_name="Schon versendet"))
    out = export(tmp_path / "review")
    page = (tmp_path / "review" / "index.html").read_text(encoding="utf-8")
    assert out["leads"] == 1
    assert "Fahrschule Muster" in page and "Schon versendet" not in page
    assert "relaunch-previews.pages.dev/fahrschule-muster-abc123/" in page
    assert "Mail 1:" in page and "Mail 3:" in page
    assert (tmp_path / "review" / "img" / "1-before.png").exists()
