# Demo-Artefakte

Erzeugt mit `pipeline demo` (offline, ohne Keys, regelbasierte Generierung) aus den fiktiven Fixtures:

| Lead | Vorher (alt, mobil) | Nachher (Entwurf, mobil) | Mail-Sequenz |
|---|---|---|---|
| Fahrschule Müller (Tabellen-Layout, © 2014) | `mueller-vorher.jpg` | `mueller-nachher.jpg` | `mail-mueller.txt` |
| Fahrschule Rote Ampel (Jimdo, keine Preise) | `rote-ampel-vorher.jpg` | `rote-ampel-nachher.jpg` | `mail-rote-ampel.txt` |
| Fahrschule Schwebe (nur JavaScript) | `schwebe-vorher.jpg` | `schwebe-nachher.jpg` | `mail-schwebe.txt` |

Mit `ANTHROPIC_API_KEY` schreibt Claude die Texte (Slogan, Über uns, Highlights) statt des regelbasierten
Composers; die Faktenfelder bleiben identisch, weil der Validator dieselben Regeln anwendet.
