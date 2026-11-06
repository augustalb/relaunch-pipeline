# Stand des Projekts (06.11.2026)

Dieses Dokument fasst zusammen, was am 05. und 06.11.2026 eingerichtet wurde, wo alles liegt und was noch fehlt.
Es enthält keine Passwörter oder Schlüssel. Die liegen nur in den jeweiligen Diensten und als Secrets bei GitHub.

---

## 1. Einfach erklärt

**Die Idee:** Viele Fahrschulen haben alte Websites, die auf dem Handy schlecht aussehen. Das Programm findet solche
Fahrschulen, baut ihnen mit ihren eigenen Inhalten einen modernen Entwurf und schreibt ihnen eine kurze, persönliche
E-Mail mit dem Link. Wer Interesse hat, antwortet. Ab dann übernehmen Sie persönlich.

**Der Ablauf in neun Schritten:**

1. **Suchen:** Google Maps liefert Fahrschulen in 30 Städten in NRW.
2. **Bewerten:** Jede Website bekommt Punkte für messbare Mängel (z. B. nicht fürs Handy gemacht, keine Verschlüsselung, langsam).
3. **Kontakt finden:** Mail-Adresse und Ansprechpartner kommen aus dem Impressum.
4. **Inhalte auslesen:** Klassen, Preise, Zeiten und Team werden von der alten Seite gesammelt.
5. **Ordnen:** Eine KI (Claude von Anthropic) sortiert die Inhalte. Ein Prüfprogramm stellt sicher, dass nichts erfunden ist.
6. **Entwurf bauen:** Daraus entsteht eine neue Website unter `preview.diaktoros.de/...`, für Suchmaschinen gesperrt.
7. **Fotos:** Vorher und Nachher werden als Handy-Screenshot festgehalten.
8. **Ihre Freigabe:** Sie sehen alles an und geben frei oder lehnen ab. Ohne Freigabe geht nichts raus.
9. **Versenden:** Instantly verschickt die Mail und zwei Nachfass-Mails, werktags zwischen 8 und 17 Uhr.

**Wo das Programm läuft:** bei GitHub („GitHub Actions“), werktags zweimal von selbst. Ihr Computer muss dafür nicht an sein.
Die automatischen Läufe sind aber **ausgeschaltet**, bis Sie die Variable `PIPELINE_ENABLED` auf `true` setzen.

**Was es kostet (Start mit 30 Mails/Tag):** etwa 32 € Google Workspace, 35–40 € Instantly, wenige Euro für Google Places
und die KI, Domains ca. 5 €. Cloudflare, Supabase und GitHub sind kostenlos.

---

## 2. Konten und Dienste

Alle Konten für dieses Projekt laufen auf **august@diaktoros.de** (Ausnahme: Domains bei Squarespace, Altbestand).

| Dienst | Wofür | Zugang für die Pipeline |
|---|---|---|
| Google Workspace (Business Starter, monatlich) | 4 Postfächer | – |
| Instantly (Growth) | Aufwärmung und Versand | später: `INSTANTLY_API_KEY`, `INSTANTLY_CAMPAIGN_ID` |
| Google Cloud, Projekt „diaktoros-pipeline“ | Places API (New), PageSpeed Insights API | `GOOGLE_PLACES_API_KEY`, `PAGESPEED_API_KEY` (je auf eine API beschränkt) |
| Anthropic | KI für Schritt 5 (`claude-haiku-5-5`) | `ANTHROPIC_API_KEY` (Ausgabenlimit gesetzt) |
| Supabase (Region eu-west-1, Irland) | Datenbank | `DATABASE_URL` (Shared/Transaction Pooler, Port 6543) |
| Cloudflare | DNS von diaktoros.de, Markenseite, Entwürfe | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` (nur „Cloudflare Pages: Edit“) |
| Squarespace | Registrar aller 4 Domains, DNS der 3 Versanddomains | – |
| GitHub `augustalb/relaunch-pipeline` | Code, automatische Läufe, Secrets | – |

**Regel:** Für dieses Projekt werden **keine claude.ai-Connectors** benutzt (siehe `CLAUDE.md`).
Claude steuert die Dienste nur über die Pipeline-Läufe bei GitHub.

---

## 3. Domains und Postfächer

Details und Hintergründe: [DOMAINS.md](DOMAINS.md).

| Domain | Rolle | DNS bei |
|---|---|---|
| diaktoros.de | Markenseite, Entwürfe unter `preview.diaktoros.de`, Verwaltungspostfach | Cloudflare (seit 06.11.2026) |
| diaktoros-growth.de | Versand | Squarespace |
| diaktoros-growth.com | Versand | Squarespace |
| diaktoros-pipeline.com | Versand | Squarespace |

Alle vier Domains laufen am **09.02.2027** ab → Verlängerung bei Squarespace prüfen.

| Postfach | Aufgabe | Instantly |
|---|---|---|
| august@diaktoros.de (+ Aliasse info@, admin@) | Verwaltung, Kontaktadresse der Website. **Versendet nie Kaltmails.** | nicht verbunden |
| a.albrecht@diaktoros-growth.de | Versand | Aufwärmung seit 05.11.2026 |
| august@diaktoros-growth.com | Versand | Aufwärmung seit 06.11.2026 |
| albrecht@diaktoros-pipeline.com | Versand | Aufwärmung seit 06.11.2026 |

Alle Postfächer leiten eine Kopie an **auguyoga@gmail.com** weiter (Kopie bleibt im Postfach, damit Instantly Antworten erkennt).
SPF, DKIM (neu erzeugt 05./06.11.2026) und DMARC sind bei allen vier Domains aktiv.

---

## 4. Website diaktoros.de

- Quellcode: `brand-site/` (Startseite, Impressum, Datenschutz). Anleitung: `brand-site/README.md`.
- Läuft als Cloudflare **Worker** `diaktoros-site`, verbunden mit GitHub: jeder Merge auf `main` veröffentlicht neu.
  Einstellung: Root directory `brand-site`, Deploy command `npx wrangler deploy`.
- Erreichbar unter diaktoros.de, www.diaktoros.de und diaktoros-site.august-albrecht.workers.dev.
- Keine Cookies, kein Tracking, Schriften selbst gehostet.
- Die alte Seite (Lovable) wird nicht mehr genutzt; ein evtl. laufendes Lovable-Abo kann gekündigt werden.

---

## 5. GitHub-Einstellungen

Unter Settings → Secrets and variables → Actions:

- **Secrets:** `DATABASE_URL`, `GOOGLE_PLACES_API_KEY`, `PAGESPEED_API_KEY`, `ANTHROPIC_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`.
  Später: `INSTANTLY_API_KEY`, `INSTANTLY_CAMPAIGN_ID`, optional `MILLIONVERIFIER_API_KEY`.
- **Variables:** `SENDER_NAME`, `SENDER_TITLE`, `SENDER_ADDRESS`, `SENDER_PHONE`, `BRAND_NAME`, `PREVIEW_DOMAIN`,
  `SENDER_BACKEND=dryrun`, `AUTO_APPROVE=false`, `REPORT_EMAIL_TO`, `PIPELINE_ENABLED=false`.

**Schlüssel prüfen:** Actions → relaunch-pipeline → Run workflow → Stufe `doctor`. Fragt jeden Dienst einmal kostenlos ab.
Erster Prüflauf am 06.11.2026: **alle fünf Dienste ok** (Datenbank, Places, PageSpeed, Anthropic, Cloudflare).

---

## 6. Wichtige Entscheidungen dieser Sitzung

- **Marke Diaktoros** statt neuer Domains: vorhandene, gealterte Domains ohne Sperrlisten-Einträge (Entscheidung 18 in [DECISIONS.md](DECISIONS.md)).
- **Rechtliches:** Anwalt hat am 05.11.2026 telefonisch Kaltakquise per Mail im konkreten Fall für zulässig gehalten.
  Schriftliche Bestätigung steht noch aus.
- **Getrenntes Verwaltungspostfach** auf diaktoros.de, damit eine Sperre eines Versandpostfachs nie den Admin-Zugang kostet.
- **Kein Öffnungs-/Klick-Tracking** in Instantly (Zustellbarkeit, Datenschutz).
- **Automatische Läufe nur mit Schalter** `PIPELINE_ENABLED`, damit vor dem ersten Test kein Geld ausgegeben wird.
- **Keine claude.ai-Connectors** für dieses Projekt.

## 7. Stolpersteine, die wir gelöst haben

- **DNS-Zwischenspeicher:** Squarespace-Einträge haben 4 Stunden Merkzeit. Neue DKIM-Schlüssel wurden deshalb erst nach
  einigen Stunden von Google erkannt. Fehlermeldung „Email authentication was not verified“ → einfach später erneut klicken.
- **Squarespace-Preset „Domain Connect to Entri“** bei diaktoros.de enthielt eigene Einträge (A, SPF, DKIM). Nie das ganze Preset löschen.
- **Cloudflare legte die Website als Worker an** und nahm zunächst das ganze Repository → `brand-site/wrangler.jsonc` begrenzt den Upload auf die Website.
- **Supabase-Pooler** verträgt keine vorbereiteten Abfragen → in `pipeline/db.py` abgeschaltet.

---

## 8. Offene Punkte und Zeitplan

1. **Testlauf mit 5 echten Fahrschulen**, noch ohne Versand (`SENDER_BACKEND=dryrun`). Danach Ergebnisse gemeinsam prüfen.
2. **`preview.diaktoros.de`** als Custom Domain des Pages-Projekts `relaunch-previews` einrichten (Projekt entsteht beim ersten Deploy).
3. **Bewertung der Websites verbessern:** PageSpeed allein ist kein gutes Maß für „veraltet“ (siehe Abschnitt 9).
4. **Schriftliche Bestätigung des Anwalts** anfordern und ablegen.
5. **Aufwärmung abwarten:** frühestens Ende November, sicherer Versandstart Anfang Dezember 2026.
6. **Instantly-Kampagne** mit 3 Schritten anlegen, `INSTANTLY_API_KEY` und `INSTANTLY_CAMPAIGN_ID` als Secrets eintragen.
7. **Erste 10 Leads von Hand prüfen**, erst danach `SENDER_BACKEND=instantly` und `PIPELINE_ENABLED=true`.
8. **Angebot vorbereiten** (390 € einmalig, 30 €/Monat), Vertrag für Hosting und Betreuung.
9. **Domains vor dem 09.02.2027 verlängern.**

## 9. Notiz zur Bewertung „schlechte Website“

PageSpeed misst Ladegeschwindigkeit und Technik, nicht, ob eine Seite veraltet aussieht. Heute machen die PageSpeed-Werte
bis zu etwa die Hälfte der Punkte aus; der Rest kommt aus eigenen Prüfungen (Handy-Darstellung, HTTPS, Tabellen-Layout,
altes Copyright-Jahr, Baukasten, kaputte Links …). Schwächen: Eine moderne, aber langsame Baukasten-Seite kann als „schlecht“
gelten; eine alt aussehende, aber schlanke Seite kann durchrutschen. Vorschlag: zusätzlich den Handy-Screenshot von der KI
nach „wirkt veraltet / unübersichtlich“ bewerten lassen und PageSpeed niedriger gewichten.
