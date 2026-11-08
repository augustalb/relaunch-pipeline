# Stand des Projekts (08.11.2026)

Dieses Dokument fasst zusammen, was vom 05. bis 08.11.2026 eingerichtet und getestet wurde, wo alles liegt und was als
Nächstes ansteht. Es enthält keine Passwörter oder Schlüssel. Die liegen nur in den jeweiligen Diensten und als Secrets bei GitHub.

---

## 0. Wo wir gerade stehen (zum Wiedereinstieg)

**Läuft:**
- Pipeline läuft vollständig bei GitHub Actions; alle Schlüssel funktionieren (Prüflauf `doctor`).
- Versand ist im **Probebetrieb** (`SENDER_BACKEND=dryrun`), automatische Läufe sind **aus** (`PIPELINE_ENABLED=false`).
- Markenseite diaktoros.de ist online.
- Aufwärmung in Instantly läuft für `august@diaktoros-growth.com` und `albrecht@diaktoros-pipeline.com`.

**Wartet auf den Betreiber:**
1. **Prüfbericht der 5 Entwürfe** (Lauf vom 06.11., IDs 66, 70, 72, 73, 76) durchsehen und entscheiden.
   - 72 (fahrschule-toennessen.de, „Fahrschule Bonn Duisdorf“): Google nennt Brühl, die Website Kardorf/Roisdorf (Bornheim) – Ort und Name prüfen.
   - 66 (Fahrschule Schulze): Mail 2 enthält noch „Layout-Shift 0.61“ mit Punkt (Befund vor der Korrektur gespeichert).
2. **Instantly-Support** zu `a.albrecht@diaktoros-growth.de` (Abschnitt 7) – Antwort abwarten.
3. **`preview.diaktoros.de` einrichten** (Cloudflare → Pages-Projekt `relaunch-previews` → Custom domains). Pflicht vor dem ersten echten Versand.
4. Optional: Gmail-Filter für DMARC-Berichte (Abschnitt 8), Lovable-Abo der alten Website kündigen.

**Danach (Reihenfolge):** weitere Testläufe in kleineren Städten → Instantly-Kampagne anlegen → erste 10 Leads von Hand
freigeben → `SENDER_BACKEND=instantly` → `PIPELINE_ENABLED=true`. Versandstart frühestens Ende November, sicherer Anfang Dezember.

---

## 1. Einfach erklärt

**Die Idee:** Viele Fahrschulen haben alte Websites, die auf dem Handy schlecht aussehen. Das Programm findet solche
Fahrschulen, baut ihnen mit ihren eigenen Inhalten einen modernen Entwurf und schreibt ihnen eine kurze, persönliche
E-Mail mit dem Link. Wer Interesse hat, antwortet. Ab dann übernehmen Sie persönlich.

**Der Ablauf in neun Schritten:**

1. **Suchen:** Google Maps liefert Fahrschulen in den Städten einer Liste (`config/cities_nrw.txt` oder `config/cities_nrw_klein.txt`).
2. **Bewerten:** Jede Website bekommt Punkte für gemessene Mängel und für einen veralteten Eindruck auf dem Handy (Abschnitt 6).
3. **Kontakt finden:** Mail-Adresse und Ansprechpartner kommen aus dem Impressum.
4. **Inhalte auslesen:** Klassen, Preise, Zeiten und Team werden von der alten Seite gesammelt.
5. **Ordnen:** Eine KI (Claude Haiku 5.5) sortiert die Inhalte. Ein Prüfprogramm stellt sicher, dass nichts erfunden ist.
6. **Entwurf bauen:** Daraus entsteht eine neue Website unter `preview.diaktoros.de/...`, für Suchmaschinen gesperrt.
7. **Fotos:** Vorher und Nachher werden als Handy-Screenshot festgehalten.
8. **Ihre Freigabe:** Prüfbericht ansehen, freigeben oder ablehnen (Abschnitt 5). Ohne Freigabe geht nichts raus.
9. **Versenden:** Instantly verschickt die Mail und zwei Nachfass-Mails, werktags zwischen 8 und 17 Uhr.

**Wo das Programm läuft:** bei GitHub („GitHub Actions“). Ihr Computer muss dafür nicht an sein.

**Was es kostet (Start mit 30 Mails/Tag):** etwa 32 € Google Workspace, 35–40 € Instantly, wenige Euro für Google Places
und die KI, Domains ca. 5 €. Cloudflare, Supabase und GitHub sind kostenlos. Alle Testläufe bisher zusammen: rund 1,30 €.

---

## 2. Konten und Dienste

Alle Konten für dieses Projekt laufen auf **august@diaktoros.de** (Ausnahme: Domains bei Squarespace, Altbestand).

| Dienst | Wofür | Zugang für die Pipeline |
|---|---|---|
| Google Workspace (Business Starter, monatlich) | 4 Postfächer | – |
| Instantly (Growth) | Aufwärmung und Versand | später: `INSTANTLY_API_KEY`, `INSTANTLY_CAMPAIGN_ID` |
| Google Cloud, Projekt „diaktoros-pipeline“ | Places API (New), PageSpeed Insights API | `GOOGLE_PLACES_API_KEY`, `PAGESPEED_API_KEY` (je auf eine API beschränkt) |
| Anthropic | KI für Inhalte und Bild-Bewertung (`claude-haiku-5-5`) | `ANTHROPIC_API_KEY` (Ausgabenlimit gesetzt) |
| Supabase (Region eu-west-1, Irland) | Datenbank | `DATABASE_URL` (Shared/Transaction Pooler, Port 6543) |
| Cloudflare | DNS von diaktoros.de, Markenseite (Worker), Entwürfe (Pages `relaunch-previews`) | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` (nur „Cloudflare Pages: Edit“) |
| Squarespace | Registrar aller 4 Domains, DNS der 3 Versanddomains | – |
| GitHub `augustalb/relaunch-pipeline` | Code, Läufe, Secrets, Prüfberichte | – |

**Regel:** Für dieses Projekt werden **keine claude.ai-Connectors** benutzt (siehe `CLAUDE.md`).
Claude steuert die Dienste nur über die Pipeline-Läufe bei GitHub.

---

## 3. Domains und Postfächer

Details und Hintergründe: [DOMAINS.md](DOMAINS.md).

| Domain | Rolle | DNS bei |
|---|---|---|
| diaktoros.de | Markenseite, Entwürfe unter `preview.diaktoros.de` (noch einzurichten), Verwaltungspostfach | Cloudflare (seit 06.11.2026) |
| diaktoros-growth.de | Versand | Squarespace |
| diaktoros-growth.com | Versand | Squarespace |
| diaktoros-pipeline.com | Versand | Squarespace |

Alle vier Domains laufen am **09.02.2027** ab → Verlängerung bei Squarespace prüfen.

| Postfach | Aufgabe | Instantly |
|---|---|---|
| august@diaktoros.de (+ Aliasse info@, admin@) | Verwaltung, Kontaktadresse der Website. **Versendet nie Kaltmails.** | nicht verbunden |
| a.albrecht@diaktoros-growth.de | Versand | **Aufwärmung startet nicht** (Abschnitt 7) |
| august@diaktoros-growth.com | Versand | Aufwärmung läuft seit 06.11.2026 |
| albrecht@diaktoros-pipeline.com | Versand | Aufwärmung läuft seit 06.11.2026 |

Alle Postfächer leiten eine Kopie an **auguyoga@gmail.com** weiter (Kopie bleibt im Postfach, damit Instantly Antworten erkennt).
SPF, DKIM (neu erzeugt 05./06.11.2026) und DMARC sind bei allen vier Domains aktiv und identisch aufgebaut.

---

## 4. Website diaktoros.de

- Quellcode: `brand-site/` (Startseite, Impressum, Datenschutz). Anleitung: `brand-site/README.md`.
- Läuft als Cloudflare **Worker** `diaktoros-site`, verbunden mit GitHub: jeder Merge auf `main` veröffentlicht neu.
  Einstellung: Root directory `brand-site`, Deploy command `npx wrangler deploy`.
- Erreichbar unter diaktoros.de, www.diaktoros.de und diaktoros-site.august-albrecht.workers.dev.
- Keine Cookies, kein Tracking, Schriften selbst gehostet.

---

## 5. Läufe starten, prüfen, freigeben

GitHub → Actions → relaunch-pipeline → **Run workflow**. Eingaben:

| Eingabe | Bedeutung |
|---|---|
| `stage` | `all` (ganzer Lauf), `doctor` (nur Schlüssel prüfen), `review` (Prüfbericht neu), `redo_review` (Entwürfe im Review neu erzeugen), `sending` (Versand freigegebener Leads), einzelne Stufen |
| `limit` | max. neue Leads pro Stufe, z. B. `20` |
| `cities_file` | Städteliste, z. B. `config/cities_nrw_klein.txt` |
| `approve` / `reject` | Lead-IDs aus dem Prüfbericht |

- **Prüfbericht:** Jeder Lauf legt unter „Artifacts“ eine ZIP ab; darin `review/index.html` mit Vorher/Nachher, Befunden,
  KI-Einschätzung, Warnungen und allen drei Mails pro Fahrschule.
- **Freigeben:** Run workflow mit `approve: 66 73`, Stufe `sending`. Bei `SENDER_BACKEND=dryrun` entstehen nur Probe-Mails (`outbox/` im Artifact).
- **GitHub-Secrets:** `DATABASE_URL`, `GOOGLE_PLACES_API_KEY`, `PAGESPEED_API_KEY`, `ANTHROPIC_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`,
  `CLOUDFLARE_API_TOKEN`. Später: `INSTANTLY_API_KEY`, `INSTANTLY_CAMPAIGN_ID`, optional `MILLIONVERIFIER_API_KEY`.
- **GitHub-Variables:** `SENDER_NAME`, `SENDER_TITLE`, `SENDER_ADDRESS`, `SENDER_PHONE`, `BRAND_NAME`, `PREVIEW_DOMAIN`,
  `SENDER_BACKEND=dryrun`, `AUTO_APPROVE=false`, `REPORT_EMAIL_TO`, `PIPELINE_ENABLED=false`.
- Jeder Lauf beginnt mit `doctor --live`: fragt jeden Dienst einmal ab und schickt das echte KI-Schema zur Probe (< 0,01 Cent).

---

## 6. Wie die Pipeline Websites bewertet (Entscheidung 19)

- **Gemessene Fakten** (dürfen in die Mail): keine Handy-Kennzeichnung, kein HTTPS, Tabellen-Layout, altes Copyright-Jahr,
  Baukasten, kaputte Unterseiten, PageSpeed-Werte, **seitliches Scrollen** auf 390 px (≤ 60 px: 6 Punkte, mehr: 18) und
  **winzige Schrift** (≥ 30 % unter 12 px: 8 Punkte).
- **KI-Urteil zum Handy-Screenshot** (nur Auswahl, **nie** im Mailtext): eindeutig veraltet/kaum bedienbar +30, etwas +10, modern −15.
  Cookie-Banner werden ignoriert.
- **PageSpeed** zählt weniger als früher, bleibt aber als nachprüfbare Zahl in der Mail.
- **Schwelle 32 Punkte.** Kalibriert am Urteil des Betreibers (Kölner Beispiele C, D, E, F sollen rein; sehr alt aussehende Seiten ebenfalls).
- Ketten mit mehreren Standorten werden nur erkannt, wenn mehrere Google-Einträge dieselbe Domain haben (offen: Erkennung über Seiteninhalte).

### Testläufe am 06.11.2026

| Lauf | Städte | Bewertet | Ausgewählt | Ergebnis |
|---|---|---|---|---|
| 1–3 | Köln | 45 | 0 | Kölner Fahrschulen meist modern; danach Bewertung überarbeitet |
| 4 | Rhein-Erft-Kreis (`config/cities_nrw_klein.txt`) | 20 | 9 | 6 mit Kontakt, 5 Entwürfe von der KI ohne Warnungen der Faktenprüfung |

**Kleinere Städte sind deutlich ergiebiger als Großstädte.** Fertig durchsuchte Suchen werden 30 Tage lang nicht wiederholt
(spart Google-Kosten). KI kostet ca. 0,5 Cent pro Entwurf, Google-Suche ca. 3 Cent pro Anfrage.

---

## 7. Offenes Problem: Aufwärmung von a.albrecht@diaktoros-growth.de

**Symptom:** In Instantly „Warmup active“, aber seit 06.11. 0 gesendet / 0 empfangen. Die beiden anderen Postfächer laufen.

**Bereits geprüft / getan:**
- DNS (MX, SPF, DKIM, DMARC) identisch zu den funktionierenden Domains.
- Manuelles Senden und Empfangen aus dem Postfach funktioniert.
- IMAP ist an, Weiterleitung nachträglich eingerichtet.
- In Instantly neu verbunden, später gelöscht und neu hinzugefügt.
- Google-Kontoaktivität: Instantly (OAuth-Client `536726988839-pt93oro4685dtb1emb0pp2vjgjol5mls`) greift regelmäßig zu → Verbindung steht, Instantly sendet trotzdem nicht. **Fehler liegt bei Instantly.**
- Google-E-Mail-Protokollsuche ist im Tarif Business Starter nicht verfügbar.
- Instantly-KI-Assistent konnte nicht helfen; **menschlicher Support angefragt, Antwort ausstehend.**

**Vermutung:** Die Adresse existierte vor ca. 9 Monaten schon in einem früheren Instantly-Konto/Arbeitsbereich und ist im
Aufwärm-Netzwerk noch belegt oder gesperrt.

**Falls der Support nicht hilft:** Postfach in Google Workspace löschen und auf derselben Domain mit neuem Namen anlegen
(z. B. august@diaktoros-growth.de; kostet nichts extra) oder per IMAP/SMTP mit App-Passwort verbinden.
**Für den Start reichen die zwei funktionierenden Postfächer** (30 Mails/Tag = 15 pro Postfach).

---

## 8. DMARC-Berichte

Google und Microsoft schicken täglich Berichte an `admin@diaktoros.de` (landen per Weiterleitung im Gmail des Betreibers).
Sie zeigen, ob Mails der Domains SPF/DKIM bestehen. Kein Handlungsbedarf. Vorschlag: Gmail-Filter `subject:(Report domain)` →
Posteingang überspringen, Label „DMARC“. Bei Zustellproblemen kann Claude einen Bericht (ZIP-Anhang) auswerten.

---

## 9. Wichtige Entscheidungen

- **Marke Diaktoros** statt neuer Domains (Entscheidung 18 in [DECISIONS.md](DECISIONS.md)).
- **Rechtliches:** Anwalt hat am 05.11.2026 telefonisch Kaltakquise per Mail im konkreten Fall für zulässig gehalten. Schriftliche Bestätigung steht noch aus.
- **Getrenntes Verwaltungspostfach** auf diaktoros.de, damit eine Sperre eines Versandpostfachs nie den Admin-Zugang kostet.
- **Kein Öffnungs-/Klick-Tracking** in Instantly.
- **Automatische Läufe nur mit Schalter** `PIPELINE_ENABLED`.
- **Keine claude.ai-Connectors** für dieses Projekt.
- **Zielgruppe bleibt: Betriebe mit bestehender, aber schwacher Website.** Ohne Website gibt es keine Mail-Adresse und keine
  eigenen Inhalte für den Entwurf; Betriebe ohne Website wären ein späterer Versuch per Brief.
- **KI-Modell:** Claude Haiku 5.5 (günstigstes); Umstellung auf Sonnet 5.5 nur, wenn die Texte im Review nicht reichen.

## 10. Stolpersteine, die gelöst sind

- **DNS-Zwischenspeicher:** Squarespace-Einträge haben 4 Stunden Merkzeit; neue DKIM-Schlüssel wurden erst nach Stunden erkannt.
- **Squarespace-Preset „Domain Connect to Entri“** bei diaktoros.de: nie das ganze Preset löschen (inzwischen DNS bei Cloudflare).
- **Cloudflare legte die Website als Worker an** → `brand-site/wrangler.jsonc` begrenzt den Upload auf die Website.
- **Supabase-Pooler** verträgt keine vorbereiteten Abfragen → in `pipeline/db.py` abgeschaltet.
- **KI-Schema abgelehnt** (erst unerlaubte Längenangaben, dann „zu komplex“) → Schema für die KI hat nur Pflichtfelder, leere Werte als `""`.
- **Falsche Fakten in ersten Entwürfen** (Firmenname aus Impressum-Floskeln, Stadt aus der Suchanfrage, Floskeln als Inhabername) → behoben.
- **Doppelte Google-Suchen** bei jedem Lauf → bereits durchsuchte Suchen werden 30 Tage übersprungen.

## 11. Offene Punkte (Gesamtliste)

1. Prüfbericht der 5 Entwürfe entscheiden (Abschnitt 0).
2. `preview.diaktoros.de` als Custom Domain von `relaunch-previews` einrichten.
3. Instantly-Support zu a.albrecht@diaktoros-growth.de (Abschnitt 7).
4. Weitere Testläufe in kleineren Städten; ggf. `config/cities_nrw_klein.txt` erweitern.
5. Ketten-Erkennung über Seiteninhalte („6x in NRW“, Filialauswahl).
6. Schriftliche Bestätigung des Anwalts anfordern und ablegen.
7. Instantly-Kampagne mit 3 Schritten anlegen, `INSTANTLY_API_KEY` und `INSTANTLY_CAMPAIGN_ID` als Secrets eintragen.
8. Erste 10 Leads von Hand prüfen, dann `SENDER_BACKEND=instantly` und `PIPELINE_ENABLED=true`.
9. Angebot vorbereiten (390 € einmalig, 30 €/Monat), Vertrag für Hosting und Betreuung.
10. Domains vor dem 09.02.2027 verlängern.
