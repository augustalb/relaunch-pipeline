from pipeline.crawl import extract_emails, extract_phones
from pipeline.http import FetchResult
from pipeline.crawl import parse_page
from pipeline.names import extract_owner, extract_company_name
from pipeline.stages.extraction import extract_candidates


def test_extract_emails_plain_and_mailto():
    html = '<a href="mailto:Info@Fahrschule-X.de">Mail</a> <p>kontakt@fahrschule-x.de</p>'
    assert extract_emails(html) == ["info@fahrschule-x.de", "kontakt@fahrschule-x.de"]


def test_extract_emails_obfuscated():
    html = "<p>info [at] fahrschule-y [dot] de</p><p>post(at)fahrschule-z.de</p><p>mail &#64; abc.de</p>"
    out = extract_emails(html)
    assert "info@fahrschule-y.de" in out
    assert "post@fahrschule-z.de" in out
    assert "mail@abc.de" in out


def test_extract_emails_ignores_assets_and_noreply():
    html = "<img src='logo@2x.png'> noreply@fahrschule.de datenschutz@fahrschule.de echt@fahrschule.de"
    assert extract_emails(html) == ["echt@fahrschule.de"]


def test_extract_emails_cloudflare():
    # "test@example.org" encoded with key 0x5a
    key = 0x5A
    enc = f"{key:02x}" + "".join(f"{ord(c) ^ key:02x}" for c in "hallo@fahrschule-cf.de")
    assert extract_emails(f'<a data-cfemail="{enc}" href="/cdn-cgi/l/email-protection">x</a>') == ["hallo@fahrschule-cf.de"]


def test_extract_phones():
    assert extract_phones("Tel. 0221 55 09 876 oder +49 211 3344556") == ["0221 55 09 876", "+49 211 3344556"]


def test_owner_and_salutation():
    assert extract_owner("Inhaber: Hans-Peter Müller\nTelefon") == ("Hans-Peter Müller", None)  # ambiguous first name -> neutral
    assert extract_owner("Inhaberin: Frau Petra Schmidt\n") == ("Petra Schmidt", "Sehr geehrte Frau Schmidt")
    assert extract_owner("Geschäftsführer: Thomas Berger\n") == ("Thomas Berger", "Sehr geehrter Herr Berger")
    assert extract_owner("Vertreten durch: Kim Lee\n") == ("Kim Lee", None)
    assert extract_owner("Angaben gemäß § 5 TMG\nFahrschule Müller GmbH\n") == (None, None)


def test_company_name_from_imprint():
    text = "Impressum\nAngaben gemäß § 5 TMG\nFahrschule Müller\nVenloer Straße 212\n"
    assert extract_company_name(text, None) == "Fahrschule Müller"


def _page(url, html, kind="start"):
    return parse_page(FetchResult(url=url, final_url=url, status=200, html=html), kind)


def test_candidates_classes_prices_hours_team_address():
    html = """<h1>Fahrschule Test</h1>
    <ul><li><b>Klasse B</b> – Pkw</li><li><b>Klasse A1</b> – 125er</li></ul>
    <table><tr><td>Grundgebühr Klasse B</td><td>299,00 €</td></tr><tr><td>Fahrstunde (45 Min.)</td><td>55,00 €</td></tr></table>
    <h3>Bürozeiten</h3><p>Mo – Fr 15:00 – 18:30 Uhr</p>
    <h3>Theorieunterricht</h3><p>Di + Do 18:30 - 20:00 Uhr</p>
    <p><b>Sabine Krause</b> – Fahrlehrerin Klasse B</p>
    <p>Fahrschule Test<br>Venloer Straße 212<br>50823 Köln</p>
    <img src="/auto.jpg" alt="Unser Auto"><img src="https://cdn.other.de/x.jpg">
    """
    url = "https://www.fahrschule-test.de/"
    cand = extract_candidates([_page(url, html)], "fahrschule-test.de")
    assert [c["name"] for c in cand["classes"]] == ["Klasse B", "Klasse A1"]
    assert {p["label"]: p["price"] for p in cand["prices"]} == {"Grundgebühr Klasse B": "299,00 €", "Fahrstunde (45 Min.)": "55,00 €"}
    assert {h["label"] for h in cand["hours"]} == {"Bürozeiten", "Theorieunterricht"}
    assert cand["team"][0]["name"] == "Sabine Krause"
    assert cand["addresses"][0]["value"] == "Venloer Straße 212, 50823 Köln"
    assert [i["url"] for i in cand["images"]] == ["https://www.fahrschule-test.de/auto.jpg"]  # foreign domain dropped
    for item in cand["classes"] + cand["prices"] + cand["hours"] + cand["team"]:
        assert item["source"] == url
