from datetime import datetime, timezone

from pipeline.http import FetchResult
from pipeline.services.pagespeed import PageSpeedResult
from pipeline.stages.scoring import analyze_html

NOW = datetime(2026, 11, 4, tzinfo=timezone.utc)


def _res(html, url="http://www.alt.de/", final=None, status=200):
    return FetchResult(url=url, final_url=final or url, status=status, html=html)


def test_old_table_site_scores_high():
    html = """<html><head><title>Alt</title></head><body bgcolor="#ffffcc"><table width="780"><tr><td><font face="Arial">Hallo</font></td></tr>
    <tr><td>x</td></tr><tr><td>y</td></tr></table><center>&copy; 2014 Fahrschule</center></body></html>"""
    r = analyze_html(_res(html), PageSpeedResult(performance=0.41, lcp_ms=8900, cls=0.31), now=NOW)
    keys = set(r.details["checks"])
    assert {"no_https", "no_viewport", "old_copyright", "legacy_tags", "psi_perf", "psi_lcp", "psi_cls"} <= keys
    assert r.score >= 80
    assert any("9 Sekunden" in f for f in r.top_findings()) or any("41 von 100" in f for f in r.top_findings())
    assert len(r.top_findings(3)) == 3


def test_modern_site_scores_low():
    html = """<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Neu</title><meta name="description" content="x">
    <meta name="viewport" content="width=device-width"><link rel="icon" href="/favicon.svg"></head><body><h1>Fahrschule Klasse B</h1>
    <img src="a.jpg" alt="a"><footer>&copy; 2026</footer></body></html>"""
    r = analyze_html(_res(html, url="https://www.neu.de/", final="https://www.neu.de/"), PageSpeedResult(performance=0.96, lcp_ms=1400, cls=0.01), now=NOW)
    assert r.score < 20, r.details


def test_unreachable_site():
    r = analyze_html(FetchResult(url="http://x.de", final_url="http://x.de", status=0, html="", error="ConnectError"), None, now=NOW)
    assert r.score == 40 and "nicht erreichbar" in r.findings[0].text


def test_findings_are_factual_sentences():
    html = '<html><head><meta name="generator" content="Jimdo Creator"></head><body>© 2019</body></html>'
    r = analyze_html(_res(html), None, now=NOW)
    for f in r.findings:
        assert f.text.endswith(".") and "Ihre" in f.text or "Website" in f.text
    assert "Jimdo-Baukasten" == r.details["builder"]


def test_broken_links_counted():
    r = analyze_html(_res("<html><body>x</body></html>"), None, internal_checks=[200, 404, 500, 200], now=NOW)
    assert r.details["internal_links_broken"] == 2
    assert any("2 von 4" in f.text for f in r.findings)
