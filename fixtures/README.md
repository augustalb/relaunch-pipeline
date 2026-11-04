# Fixtures

Acht **fiktive** Fahrschul-Websites (alle Namen, Adressen, Nummern erfunden) in unterschiedlichen
„Schlechtheitsgraden“, erzeugt von `build_fixtures.py`:

| Ordner | Stil | Besonderheit |
|---|---|---|
| fahrschule-mueller | Tabellen-Layout, `<font>`, kein Doctype, bgcolor | © 2014, sehr langsam (PSI-Mock) |
| fahrschule-drive-in | FrontPage, `<marquee>`, Comic Sans | E-Mail verschleiert „(at)“, Inhaberin ohne Anrede-Marker |
| fahrschule-rote-ampel | Jimdo-Baukasten, Mixed Content | keine Preise (Sektion muss ausgeblendet werden) |
| fahrschule-fahrspass-essen | kein viewport, jQuery 1.7 | E-Mail „[at] … [dot]“ |
| fahrschule-kurvenkoenig | „im Aufbau“, `<blink>`, kein Impressum-Team | sehr dünner Inhalt |
| fahrschule-wuppertaler-schwebe | Inhalt nur per JavaScript | braucht Playwright-Rendering |
| fahrschule-bonn-mobil | IONOS MyWebsite, jQuery 1.11 | normale Seite 2018 |
| fahrschule-muenster-modern | modern, schnell | **Kontrollfall**: muss unter dem Schwellenwert bleiben |

`places.json` enthält zusätzlich Einträge ohne Website, auf Facebook, dauerhaft geschlossen, eine Kette
und einen zweiten Standort mit gleicher Domain, um die Ausschlussregeln zu testen. `pagespeed.json`
liefert die PageSpeed-Werte für den Mock.

Neu erzeugen: `python fixtures/build_fixtures.py`
