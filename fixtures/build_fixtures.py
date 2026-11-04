"""Generates the fictional driving-school websites in fixtures/sites/ (run: python fixtures/build_fixtures.py).

Eight schools, each with a different kind of "bad": table layout, <font> tags, no viewport,
Jimdo/IONOS builder markers, old copyright, under-construction banner, JS-only content,
obfuscated e-mail addresses, broken links. All names, addresses and numbers are invented.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent
SITES = ROOT / "sites"

SCHOOLS = [
    {
        "slug": "fahrschule-mueller",
        "name": "Fahrschule Müller",
        "city": "Köln",
        "owner": "Hans-Peter Müller",
        "owner_title": "Herr",
        "street": "Venloer Straße 212",
        "zip": "50823",
        "phone": "0221 5509876",
        "email": "info@fahrschule-mueller-koeln.de",
        "obfuscate": False,
        "classes": ["B", "BE", "A", "A2", "A1", "AM"],
        "prices": [("Grundgebühr Klasse B", "299,00 €"), ("Fahrstunde (45 Min.)", "55,00 €"), ("Sonderfahrt (45 Min.)", "65,00 €"), ("Vorstellung praktische Prüfung", "180,00 €")],
        "hours": [("Bürozeiten", ["Mo – Fr 15:00 – 18:30 Uhr"]), ("Theorieunterricht", ["Di + Do 18:30 – 20:00 Uhr"])],
        "team": [("Hans-Peter Müller", "Inhaber, Fahrlehrer Klasse A/B/BE"), ("Sabine Krause", "Fahrlehrerin Klasse B"), ("Murat Yilmaz", "Fahrlehrer Klasse A/B")],
        "about": "Seit vielen Jahren bilden wir in Köln-Ehrenfeld Fahrschüler aus. Bei uns lernst du in kleinen Gruppen, mit modernen Fahrzeugen und festen Ansprechpartnern. Wir nehmen uns Zeit für jede Frage und begleiten dich bis zur bestandenen Prüfung.",
        "style": "table",
        "year": 2014,
        "extras": ["Intensivkurs in den Ferien", "Ausbildung auch mit Automatik", "Begleitetes Fahren ab 17 (BF17)"],
    },
    {
        "slug": "fahrschule-drive-in",
        "name": "Fahrschule Drive-In Schmidt",
        "city": "Düsseldorf",
        "owner": "Petra Schmidt",
        "owner_title": None,
        "street": "Bilker Allee 88",
        "zip": "40217",
        "phone": "0211 3344556",
        "email": "kontakt@drive-in-schmidt.de",
        "obfuscate": True,
        "classes": ["B", "B197", "BE"],
        "prices": [("Grundbetrag", "350 €"), ("Übungsfahrt 45 Min", "58 €"), ("Nachtfahrt", "70 €")],
        "hours": [("Öffnungszeiten Büro", ["Montag bis Donnerstag 16:00 - 19:00 Uhr", "Freitag 15:00 - 17:00 Uhr"]), ("Theorie", ["Mo, Mi 19:00 - 20:30 Uhr"])],
        "team": [("Petra Schmidt", "Inhaberin und Fahrlehrerin")],
        "about": "Die Fahrschule Drive-In Schmidt ist eine kleine, persönliche Fahrschule in Düsseldorf-Bilk. Wir bilden ausschließlich in der Klasse B aus und konzentrieren uns darauf, dich entspannt und sicher durch die Prüfung zu bringen.",
        "style": "font",
        "year": 2011,
        "extras": ["Automatik-Ausbildung B197"],
    },
    {
        "slug": "fahrschule-rote-ampel",
        "name": "Fahrschule Rote Ampel",
        "city": "Dortmund",
        "owner": "Thomas Berger",
        "owner_title": "Herr",
        "street": "Brückstraße 14",
        "zip": "44135",
        "phone": "0231 9876543",
        "email": "post@rote-ampel-dortmund.de",
        "obfuscate": False,
        "classes": ["B", "BE", "L", "T", "C", "CE"],
        "prices": [],
        "hours": [("Bürozeiten", ["Mo - Fr 10:00 - 12:00 Uhr", "Mo - Do 15:00 - 18:00 Uhr"]), ("Theorieunterricht", ["Mo + Mi 18:00 - 19:30 Uhr", "Sa 10:00 - 11:30 Uhr"])],
        "team": [("Thomas Berger", "Inhaber, Fahrlehrer alle Klassen"), ("Kevin Nowak", "Fahrlehrer Klasse B/BE"), ("Anja Lehmann", "Büro")],
        "about": "Pkw, Anhänger, Traktor oder Lkw: Bei der Fahrschule Rote Ampel in der Dortmunder Innenstadt bekommst du alles aus einer Hand. Unsere Fahrlehrer kennen die Prüfstrecken genau und bereiten dich gezielt vor.",
        "style": "jimdo",
        "year": 2019,
        "extras": ["Lkw-Ausbildung C/CE", "Erste-Hilfe-Kurs im Haus"],
    },
    {
        "slug": "fahrschule-fahrspass-essen",
        "name": "Fahrschule FahrSpaß Essen",
        "city": "Essen",
        "owner": "Ayşe Demir",
        "owner_title": "Frau",
        "street": "Rüttenscheider Str. 101",
        "zip": "45130",
        "phone": "0201 7788990",
        "email": "info@fahrspass-essen.de",
        "obfuscate": True,
        "classes": ["B", "B196", "A1", "A2", "A"],
        "prices": [("Grundgebühr Klasse B", "320,00 €"), ("Grundgebühr Klasse A", "380,00 €"), ("Fahrstunde 45 Min.", "59,00 €"), ("Lernmaterial", "80,00 €")],
        "hours": [("Bürozeiten", ["Mo – Fr 14:00 – 18:00 Uhr"]), ("Theorieunterricht", ["Mo – Do 18:00 – 19:30 Uhr"])],
        "team": [("Ayşe Demir", "Inhaberin, Fahrlehrerin A/B"), ("Jonas Weber", "Fahrlehrer Klasse B")],
        "about": "FahrSpaß Essen steht für entspanntes Lernen in Rüttenscheid. Motorrad oder Auto, wir finden das passende Tempo für dich. Theorie gibt es viermal pro Woche, Fahrstunden auch samstags.",
        "style": "noviewport",
        "year": 2017,
        "extras": ["Motorradausbildung A, A2, A1", "B196 Aufstieg für Autofahrer", "Fahrstunden auch samstags"],
    },
    {
        "slug": "fahrschule-kurvenkoenig",
        "name": "Fahrschule Kurvenkönig",
        "city": "Bochum",
        "owner": "Michael Hartmann",
        "owner_title": None,
        "street": "Castroper Straße 45",
        "zip": "44791",
        "phone": "0234 123456",
        "email": "fahrschule-kurvenkoenig@t-online.de",
        "obfuscate": False,
        "classes": ["B", "A", "A2"],
        "prices": [("Grundgebühr", "289,00 €"), ("Fahrstunde", "52,00 €")],
        "hours": [("Theorie", ["Di + Do 18:00 - 19:30 Uhr"])],
        "team": [],
        "about": "Fahrschule Kurvenkönig in Bochum. Auto- und Motorradführerschein, individuell und fair.",
        "style": "construction",
        "year": 2012,
        "extras": [],
    },
    {
        "slug": "fahrschule-wuppertaler-schwebe",
        "name": "Fahrschule Schwebe",
        "city": "Wuppertal",
        "owner": "Gerd Vogel",
        "owner_title": "Herr",
        "street": "Friedrich-Ebert-Straße 160",
        "zip": "42117",
        "phone": "0202 445566",
        "email": "info@fahrschule-schwebe.de",
        "obfuscate": False,
        "classes": ["B", "BE", "B197"],
        "prices": [("Grundgebühr Klasse B", "310,00 €"), ("Fahrstunde (45 Minuten)", "56,00 €"), ("Überlandfahrt", "68,00 €"), ("Autobahnfahrt", "68,00 €"), ("Nachtfahrt", "68,00 €")],
        "hours": [("Bürozeiten", ["Mo, Di, Do 15:30 - 18:00 Uhr"]), ("Theorieunterricht", ["Mo + Do 18:00 - 19:30 Uhr"])],
        "team": [("Gerd Vogel", "Inhaber, Fahrlehrer"), ("Lena Vogel", "Fahrlehrerin Klasse B"), ("Stefan Koch", "Fahrlehrer Klasse B/BE")],
        "about": "Familienbetrieb an der Friedrich-Ebert-Straße im Herzen von Elberfeld. Wir bilden in den Klassen B, BE und B197 aus und legen Wert auf eine ruhige, geduldige Atmosphäre im Auto.",
        "style": "jsonly",
        "year": 2021,
        "extras": ["Automatik mit B197", "Intensivkurs in 3 Wochen"],
    },
    {
        "slug": "fahrschule-bonn-mobil",
        "name": "Fahrschule Bonn Mobil",
        "city": "Bonn",
        "owner": "Claudia Fischer",
        "owner_title": "Frau",
        "street": "Kölnstraße 230",
        "zip": "53117",
        "phone": "0228 665544",
        "email": "info@bonn-mobil-fahrschule.de",
        "obfuscate": True,
        "classes": ["B", "A1", "AM", "BE"],
        "prices": [("Grundgebühr Klasse B", "330,00 €"), ("Fahrstunde", "57,00 €")],
        "hours": [("Bürozeiten", ["Mo – Do 16:00 – 18:30 Uhr"]), ("Theorie", ["Di + Do 18:30 – 20:00 Uhr"])],
        "team": [("Claudia Fischer", "Inhaberin, Fahrlehrerin"), ("Daniel Roth", "Fahrlehrer")],
        "about": "Bonn Mobil ist deine Fahrschule in Bonn-Nord. Wir holen dich auf Wunsch zur Fahrstunde ab und planen Termine flexibel um Schule, Uni und Job herum.",
        "style": "ionos",
        "year": 2018,
        "extras": ["Abholung zur Fahrstunde", "Flexible Termine"],
    },
    {
        "slug": "fahrschule-muenster-modern",
        "name": "Fahrschule Westfalen",
        "city": "Münster",
        "owner": "Julia Brinkmann",
        "owner_title": "Frau",
        "street": "Hammer Straße 300",
        "zip": "48153",
        "phone": "0251 9988776",
        "email": "hallo@fahrschule-westfalen.de",
        "obfuscate": False,
        "classes": ["B", "B197", "BE", "A2"],
        "prices": [("Grundgebühr Klasse B", "349,00 €"), ("Fahrstunde", "60,00 €")],
        "hours": [("Bürozeiten", ["Mo – Fr 15:00 – 18:00 Uhr"]), ("Theorieunterricht", ["Mo – Mi 18:00 – 19:30 Uhr"])],
        "team": [("Julia Brinkmann", "Inhaberin, Fahrlehrerin"), ("Tim Schulte", "Fahrlehrer")],
        "about": "Moderne Fahrschule am Hammer-Straßen-Kreisel. Online-Theorie, digitale Terminbuchung und neue Fahrzeuge.",
        "style": "modern",  # control case: should score below threshold
        "year": 2026,
        "extras": ["Online-Theorie", "Digitale Terminbuchung"],
    },
]

CLASS_TEXT = {
    "B": "Pkw bis 3,5 t",
    "B196": "Leichtkraftrad mit Klasse B",
    "B197": "Automatik ohne Beschränkung",
    "BE": "Pkw mit Anhänger",
    "A": "Motorrad unbeschränkt",
    "A1": "Leichtkrafträder 125 ccm",
    "A2": "Motorrad bis 35 kW",
    "AM": "Roller bis 45 km/h",
    "L": "Zugmaschinen",
    "T": "Traktor",
    "C": "Lkw",
    "CE": "Lkw mit Anhänger",
}


def email_html(sc: dict) -> str:
    e = sc["email"]
    if sc["obfuscate"]:
        if sc["slug"].endswith("essen"):
            return e.replace("@", " [at] ").replace(".", " [dot] ")
        return e.replace("@", "(at)")
    return f'<a href="mailto:{e}">{e}</a>'


def imprint(sc: dict) -> str:
    title = f"{sc['owner_title']} " if sc["owner_title"] else ""
    return f"""<h1>Impressum</h1>
<p>Angaben gemäß § 5 TMG</p>
<p>{sc['name']}<br>{sc['street']}<br>{sc['zip']} {sc['city']}</p>
<p>Inhaber: {title}{sc['owner']}</p>
<p>Telefon: {sc['phone']}<br>E-Mail: {email_html(sc)}</p>
<p>Umsatzsteuer-ID: DE123456789 (fiktiv)</p>
<p>Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV: {sc['owner']}</p>
<p>Diese Website ist eine fiktive Test-Fixture. Alle Angaben sind erfunden.</p>
<p><a href="index.html">Zurück zur Startseite</a></p>"""


def classes_html(sc: dict) -> str:
    items = "".join(f"<li><b>Klasse {c}</b> – {CLASS_TEXT.get(c, '')}</li>" for c in sc["classes"])
    return f"<h2>Unsere Führerscheinklassen</h2><ul>{items}</ul>"


def prices_html(sc: dict) -> str:
    if not sc["prices"]:
        return "<h2>Preise</h2><p>Preise auf Anfrage – rufen Sie uns an oder kommen Sie vorbei.</p>"
    rows = "".join(f"<tr><td>{l}</td><td>{p}</td></tr>" for l, p in sc["prices"])
    return f"<h2>Preisliste</h2><table border=\"1\" cellpadding=\"4\">{rows}</table><p>Alle Preise inkl. MwSt. Stand {sc['year']}.</p>"


def hours_html(sc: dict) -> str:
    out = ""
    for label, entries in sc["hours"]:
        out += f"<h3>{label}</h3>" + "".join(f"<p>{e}</p>" for e in entries)
    return out


def team_html(sc: dict) -> str:
    if not sc["team"]:
        return ""
    return "<h2>Unser Team</h2>" + "".join(f"<p><b>{n}</b> – {r}</p>" for n, r in sc["team"])


def extras_html(sc: dict) -> str:
    return "".join(f"<li>{x}</li>" for x in sc["extras"])


def wrap(sc: dict, body: str, title: str, page: str) -> str:
    st = sc["style"]
    nav = '<a href="index.html">Start</a> | <a href="klassen.html">Führerscheinklassen</a> | <a href="preise.html">Preise</a> | <a href="team.html">Team</a> | <a href="kontakt.html">Kontakt</a> | <a href="impressum.html">Impressum</a>'
    if st == "table":
        return f"""<html><head><title>{title}</title><meta http-equiv="Content-Type" content="text/html; charset=utf-8"></head>
<body bgcolor="#FFFFCC" text="#000000" link="#0000FF">
<table width="780" border="0" cellpadding="6" cellspacing="0" align="center" bgcolor="#FFFFFF">
<tr><td colspan="2" bgcolor="#000080"><font face="Arial" size="5" color="#FFFFFF"><b>{sc['name']}</b></font></td></tr>
<tr><td width="180" valign="top" bgcolor="#E0E0E0"><font face="Arial" size="2">{nav.replace(' | ', '<br><br>')}</font></td>
<td valign="top"><font face="Arial" size="2">{body}</font></td></tr>
<tr><td colspan="2" align="center"><font face="Arial" size="1">&copy; {sc['year']} {sc['name']} &middot; <a href="impressum.html">Impressum</a> &middot; <a href="datenschutz.html">Datenschutz</a></font></td></tr>
</table></body></html>"""
    if st == "font":
        return f"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html><head><title>{title}</title><meta http-equiv="Content-Type" content="text/html; charset=utf-8"><meta name="generator" content="Microsoft FrontPage 6.0"></head>
<body background="bg.gif" bgcolor="#C0C0C0"><center><font face="Comic Sans MS" size="6" color="#800000"><b>{sc['name']}</b></font><br>
<marquee>Herzlich willkommen auf unserer Homepage! Jetzt anmelden!</marquee><hr>
<font face="Verdana" size="2">{nav}</font><hr>
<div align="left"><font face="Verdana" size="2">{body}</font></div><hr>
<font size="1">&copy; {sc['year']} {sc['name']} | <a href="impressum.html">Impressum</a> | <a href="datenschutz.html">Datenschutz</a> | <a href="gaestebuch.html">Gästebuch</a> | <a href="links.html">Links</a></font></center></body></html>"""
    if st == "jimdo":
        return f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><title>{title}</title><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="generator" content="Jimdo Creator">
<link rel="stylesheet" href="https://assets.jimstatic.com/web.css.a1b2c3.css"><script src="http://assets.jimstatic.com/app.js"></script></head>
<body class="jimdo-template"><div id="content_area"><div class="jtpl-header"><span class="jtpl-logo">{sc['name']}</span></div><nav class="jtpl-navigation">{nav}</nav>
<div class="j-module n j-text">{body}</div>
<footer class="jtpl-footer"><p>&copy; {sc['year']} {sc['name']} &middot; <a href="impressum.html">Impressum</a> &middot; <a href="datenschutz.html">Datenschutz</a></p><a href="https://www.jimdo.com">Diese Webseite wurde mit Jimdo erstellt!</a></footer></div></body></html>"""
    if st == "noviewport":
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title}</title><link rel="stylesheet" href="style.css"><script src="jquery-1.7.2.min.js"></script></head>
<body><div id="wrapper" style="width:960px;margin:0 auto"><div id="header"><h1>{sc['name']}</h1><p>Fahrschule in {sc['city']}</p></div><div id="nav">{nav}</div>
<div id="content">{body}</div>
<div id="footer">&copy; {sc['year']} {sc['name']} | <a href="impressum.html">Impressum</a> | <a href="datenschutz.html">Datenschutz</a></div></div></body></html>"""
    if st == "construction":
        return f"""<html><head><title>{title}</title></head><body bgcolor="#FFFFFF">
<center><img src="logo.gif" width="300"><br><h1><font color="red">{sc['name']}</font></h1>
<p><blink>Diese Seite befindet sich noch im Aufbau!</blink></p>
<table width="600" align="center"><tr><td>{nav}</td></tr><tr><td>{body}</td></tr></table>
<p><font size="1">Letzte Änderung: {sc['year']} &middot; <a href="impressum.html">Impressum</a></font></p></center></body></html>"""
    if st == "jsonly":
        # content is rendered client-side; HTML only contains a loader + data blob
        data = json.dumps(body)
        return f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><title>{title}</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{{font-family:Arial}}</style></head>
<body><div id="app"><noscript>Bitte JavaScript aktivieren.</noscript></div>
<script>var NAV={json.dumps(nav)};var CONTENT={data};document.getElementById('app').innerHTML='<header><h1>{sc['name']}</h1><nav>'+NAV+'</nav></header><main>'+CONTENT+'</main><footer>&copy; {sc['year']} {sc['name']} · <a href=\\"impressum.html\\">Impressum</a> · <a href=\\"datenschutz.html\\">Datenschutz</a></footer>';</script>
</body></html>"""
    if st == "ionos":
        return f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><title>{title}</title><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="generator" content="1&1 IONOS MyWebsite">
<link rel="stylesheet" href="https://cdn.website-start.de/proxy/apps/static/css/base.css"><script type="text/javascript" src="https://cdn.website-start.de/app/cdn/js/jquery-1.11.3.min.js"></script></head>
<body class="mywebsite"><div class="header"><div class="logo">{sc['name']}</div><div class="slogan">Fahrschule in {sc['city']}</div></div><div class="nav">{nav}</div>
<div class="main">{body}</div>
<div class="footer">&copy; {sc['year']} {sc['name']} · <a href="impressum.html">Impressum</a> · <a href="datenschutz.html">Datenschutz</a> · <a href="sitemap.html">Sitemap</a></div></body></html>"""
    # modern control case
    return f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><title>{title}</title><meta name="description" content="{sc['name']} – Fahrschule in {sc['city']}"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="icon" href="favicon.svg">
<style>body{{font-family:system-ui;margin:0;color:#111}}header{{background:#0f766e;color:#fff;padding:24px}}nav a{{color:#fff;margin-right:12px}}main{{max-width:900px;margin:0 auto;padding:24px}}</style></head>
<body><header><h1>{sc['name']}</h1><nav>{nav}</nav></header><main>{body}</main>
<footer style="padding:24px;text-align:center">&copy; {sc['year']} {sc['name']} · <a href="impressum.html">Impressum</a> · <a href="datenschutz.html">Datenschutz</a></footer></body></html>"""


def _write_photo(path: Path, label: str, size: tuple[int, int], rgb: tuple[int, int, int]) -> None:
    """A generated 'photo' (gradient + label) standing in for a business's own picture."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:  # pragma: no cover
        path.write_bytes(b"")
        return
    w, h = size
    im = Image.new("RGB", size)
    px = im.load()
    for y in range(h):
        f = y / h
        for x in range(w):
            g = x / w
            px[x, y] = (int(rgb[0] + 80 * g), int(rgb[1] + 60 * f), int(rgb[2] + 50 * (1 - g)))
    ImageDraw.Draw(im).text((40, h - 60), f"{label} (fiktives Foto)", fill=(255, 255, 255))
    im.save(path, "JPEG", quality=80)


def build() -> None:
    places = []
    for i, sc in enumerate(SCHOOLS):
        d = SITES / sc["slug"]
        d.mkdir(parents=True, exist_ok=True)
        start = f"""<h1>Willkommen bei der {sc['name']}</h1>
<p>{sc['about']}</p>
<ul>{extras_html(sc)}</ul>
{classes_html(sc)}
{hours_html(sc)}
<p>Rufen Sie uns an: <b>{sc['phone']}</b> oder schreiben Sie an {email_html(sc)}.</p>
<p><img src="auto.jpg" width="400" alt=""> <img src="theorieraum.jpg" width="400" alt=""></p>"""
        (d / "index.html").write_text(wrap(sc, start, f"{sc['name']} - Fahrschule in {sc['city']}" if sc["style"] != "font" else "Startseite", "index"), encoding="utf-8")
        (d / "klassen.html").write_text(wrap(sc, classes_html(sc) + "<p>Fragen zur Ausbildung? Wir beraten Sie gern persönlich.</p>", "Führerscheinklassen", "klassen"), encoding="utf-8")
        (d / "preise.html").write_text(wrap(sc, prices_html(sc), "Preise", "preise"), encoding="utf-8")
        (d / "team.html").write_text(wrap(sc, team_html(sc) or "<h2>Team</h2><p>Infos folgen.</p>", "Team", "team"), encoding="utf-8")
        (d / "kontakt.html").write_text(wrap(sc, f"<h2>Kontakt & Anfahrt</h2><p>{sc['name']}<br>{sc['street']}<br>{sc['zip']} {sc['city']}</p><p>Tel. {sc['phone']}<br>{email_html(sc)}</p>{hours_html(sc)}", "Kontakt", "kontakt"), encoding="utf-8")
        (d / "impressum.html").write_text(wrap(sc, imprint(sc), "Impressum", "impressum"), encoding="utf-8")
        (d / "datenschutz.html").write_text(wrap(sc, "<h1>Datenschutzerklärung</h1><p>Fiktiver Platzhaltertext. Verantwortlich: " + sc["name"] + ", " + sc["street"] + ", " + sc["zip"] + " " + sc["city"] + ".</p>", "Datenschutz", "datenschutz"), encoding="utf-8")
        # image fixtures: two schools have usable own photos (generated), the rest only a 1x1 placeholder
        if sc["slug"] in ("fahrschule-rote-ampel", "fahrschule-bonn-mobil"):
            _write_photo(d / "auto.jpg", sc["name"], (1400, 900), (30, 60, 120))
            _write_photo(d / "theorieraum.jpg", "Theorieraum", (1200, 800), (90, 110, 70))
        for img in ("auto.jpg", "theorieraum.jpg") if sc["slug"] not in ("fahrschule-rote-ampel", "fahrschule-bonn-mobil") else ():
            (d / img).write_bytes(bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f0000010501010101010100000000000000000102030405060708090a0bffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda0008010100003f00fbd3ffd9"))
        places.append(
            {
                "place_id": f"ChIJfixture{i:02d}{sc['slug'][-6:]}",
                "name": sc["name"],
                "city": sc["city"],
                "address": f"{sc['street']}, {sc['zip']} {sc['city']}, Deutschland",
                "phone": sc["phone"],
                "website": f"/{sc['slug']}/",
                "rating": 4.3 + (i % 5) / 10,
                "rating_count": 20 + i * 17,
                "business_status": "OPERATIONAL",
            }
        )
    # extra entries exercising the exclusion rules
    places += [
        {"place_id": "ChIJfixture90nosite", "name": "Fahrschule Ohne Netz", "city": "Köln", "address": "Irgendwo 1, 50667 Köln", "phone": "0221 1", "website": None, "rating": 4.0, "rating_count": 3, "business_status": "OPERATIONAL"},
        {"place_id": "ChIJfixture91facebook", "name": "Fahrschule Nur Facebook", "city": "Köln", "address": "Irgendwo 2, 50667 Köln", "phone": "0221 2", "website": "https://www.facebook.com/fahrschulenurfb", "rating": 4.9, "rating_count": 12, "business_status": "OPERATIONAL"},
        {"place_id": "ChIJfixture92closed", "name": "Fahrschule Geschlossen", "city": "Düsseldorf", "address": "Weg 3, 40210 Düsseldorf", "phone": "0211 3", "website": "https://www.fahrschule-zu.de", "rating": 3.1, "rating_count": 8, "business_status": "CLOSED_PERMANENTLY"},
        {"place_id": "ChIJfixture93chain", "name": "123fahrschule Köln", "city": "Köln", "address": "Ring 4, 50668 Köln", "phone": "0221 4", "website": "https://www.123fahrschule.de/koeln", "rating": 4.5, "rating_count": 300, "business_status": "OPERATIONAL"},
        {"place_id": "ChIJfixture94dupdomain", "name": "Fahrschule Müller Filiale Nippes", "city": "Köln", "address": "Neusser Str. 5, 50733 Köln", "phone": "0221 5509876", "website": "/fahrschule-mueller/", "rating": 4.4, "rating_count": 9, "business_status": "OPERATIONAL"},
    ]
    (ROOT / "places.json").write_text(json.dumps(places, ensure_ascii=False, indent=2), encoding="utf-8")
    psi = {
        "fahrschule-mueller": {"performance": 0.41, "lcp_ms": 8900, "cls": 0.31, "accessibility": 0.62, "best_practices": 0.5, "seo": 0.7},
        "fahrschule-drive-in": {"performance": 0.55, "lcp_ms": 5200, "cls": 0.05, "accessibility": 0.58, "best_practices": 0.6, "seo": 0.6},
        "fahrschule-rote-ampel": {"performance": 0.38, "lcp_ms": 9800, "cls": 0.12, "accessibility": 0.8, "best_practices": 0.7, "seo": 0.85},
        "fahrschule-fahrspass-essen": {"performance": 0.63, "lcp_ms": 4300, "cls": 0.02, "accessibility": 0.7, "best_practices": 0.65, "seo": 0.75},
        "fahrschule-kurvenkoenig": {"performance": 0.7, "lcp_ms": 3100, "cls": 0.0, "accessibility": 0.4, "best_practices": 0.5, "seo": 0.45},
        "fahrschule-wuppertaler-schwebe": {"performance": 0.35, "lcp_ms": 7600, "cls": 0.4, "accessibility": 0.75, "best_practices": 0.8, "seo": 0.5},
        "fahrschule-bonn-mobil": {"performance": 0.47, "lcp_ms": 6100, "cls": 0.18, "accessibility": 0.72, "best_practices": 0.6, "seo": 0.8},
        "fahrschule-muenster-modern": {"performance": 0.96, "lcp_ms": 1400, "cls": 0.01, "accessibility": 0.97, "best_practices": 1.0, "seo": 1.0},
    }
    (ROOT / "pagespeed.json").write_text(json.dumps(psi, indent=2), encoding="utf-8")
    print(f"built {len(SCHOOLS)} fixture sites, {len(places)} places")


if __name__ == "__main__":
    build()
