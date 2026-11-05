# Relaunch-Pipeline – automatische Akquise für Website-Relaunches

Findet lokale Betriebe in Deutschland mit messbar schlechter Website, baut aus deren eigenen Inhalten
eine deutlich bessere Preview-Website und schickt eine kurze, persönliche E-Mail mit dem Link.
Antworten landen bei `auguyoga@gmail.com`; ab da übernimmst du manuell.

Erste Branche: **Fahrschulen**, Startregion **NRW** (30 Städte in `config/cities_nrw.txt`).
Weitere Branchen = neuer Ordner unter `industries/`, kein Code nötig.

Alles läuft **ohne Keys im Dry-Run** (`pipeline demo`), degradiert pro Stufe sauber, wenn ein Key fehlt,
und täglich unbeaufsichtigt in GitHub Actions.

```bash
git clone https://github.com/augustalb/relaunch-pipeline && cd relaunch-pipeline
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]" && python -m playwright install chromium
(cd site && npm ci)
pipeline demo          # kompletter Offline-Durchlauf mit 8 fiktiven Fahrschulen
pipeline review        # Review-UI auf http://127.0.0.1:8787
pipeline doctor        # welche Keys/Tools fehlen, was degradiert
```

Ergebnisse des Demo-Laufs: `docs/demo/` (3 Vorher/Nachher-Screenshots, 3 fertige Mail-Sequenzen).

---

## 1. Was das System tut

```mermaid
flowchart LR
    subgraph Täglich["GitHub Actions · Mo–Fr 07:40 + 12:40 UTC"]
        H[Housekeeping<br/>Ablauf 45 Tage · Places-Cache 30 Tage] --> S0[Status-Sync<br/>Antworten · Bounces · Abmeldungen → Sperrliste]
        S0 --> D[1 Discovery<br/>Google Places Text Search]
        D --> S[2 Scoring<br/>PageSpeed mobil + eigene Checks → 0–100]
        S --> C[3 Kontakt<br/>Impressum/Kontakt crawlen · E-Mail · Anrede · MX/Verifizierung]
        C --> E[4 Extraktion<br/>bis 8 Seiten · Playwright · Klassen · Preise · Zeiten · Team · Bilder]
        E --> G[5 Generierung<br/>Claude Haiku 5.5 → striktes JSON-Schema<br/>Validator gegen erfundene Fakten]
        G --> P[6 Preview<br/>Astro + Tailwind → Cloudflare Pages<br/>/slug-xxxxxx · noindex]
        P --> SC[7 Screenshots<br/>Playwright mobil alt/neu]
        SC --> R{8 Review<br/>pending_review}
        R -->|freigeben| Q[9 Versand<br/>Sender-Interface · Limits · Mo–Fr 8–17 Uhr]
        Q --> I[Instantly<br/>Warm-up · Rotation · Follow-ups]
    end
    I -->|Antwort| M[auguyoga@gmail.com]
    M -->|Abschluss| PR[pipeline promote<br/>eigenes Pages-Projekt + DNS-Anleitung]
    DB[(Supabase Postgres<br/>lokal: SQLite)] --- D & S & C & E & G & P & Q
```

**Statuskette je Lead** (Tabelle `leads`, jede Stufe liest nur ihren Eingangsstatus, ist idempotent):

`discovered → scored → qualified | disqualified → contact_found | no_contact → extracted → generated → pending_review → approved | rejected → queued → sent → replied | bounced | unsubscribed → won | lost`, zusätzlich `expired`.

### Ordnerstruktur

| Pfad | Inhalt |
|---|---|
| `pipeline/` | Python-Paket. `cli.py` (eine CLI), `config.py` (alle Einstellungen), `db.py` (SQLAlchemy-Modelle), `schema.py` (Content-Schema), `validator.py` (Faktencheck), `stages/` (eine Datei je Stufe), `services/` (Places, PageSpeed, LLM, Sender, Cloudflare, Verifier, Sperrliste), `review/` (Web-UI) |
| `industries/fahrschulen/` | Branchenpaket: `industry.yaml`, `email/` (Mail-Vorlagen, editierbar), `site/Template.astro`, `site/images/` + `LICENSES.md` |
| `site/` | Astro-Projekt für alle Previews (ein Deployment). Previews liegen als JSON in `site/src/data/previews/` |
| `config/` | Städte, Sperrlisten, Plattform-Domains (Textdateien) |
| `fixtures/` | 8 fiktive Fahrschul-Websites + Places/PageSpeed-Mocks für Demo und Tests |
| `tests/` | Unit-Tests + End-to-End-Test des Demo-Laufs (`python -m pytest`) |
| `customers/` | Produktionsprojekte aus `pipeline promote` (JSON + DNS-Anleitung) |
| `outbox/` | Dry-Run-Mails als `.eml` |
| `docs/` | `DECISIONS.md`, `GO-LIVE.md`, `demo/` |

### CLI

```
pipeline run --stage all [--limit N] [--no-deploy] [--force-window]
pipeline run --stage discovery|scoring|contact|extraction|generation|preview|screenshots|sending|sync|housekeeping|report
pipeline review                 # Web-UI: Vorher/Nachher, Befunde, Validator, Mail bearbeiten, (Sammel-)Freigabe
pipeline report [--days 7] [--email]
pipeline promote <lead-id|slug> --domain fahrschule-x.de
pipeline demo                   # Offline-Durchlauf mit Fixtures
pipeline leads [--status pending_review]
pipeline approve 12 13 / pipeline reject 14 --reason "..."
pipeline block info@x.de x.de   # globale Sperrliste
pipeline doctor
```

---

## 2. Setup-Checkliste (Schritt für Schritt)

### 2.1 Accounts und Keys

| # | Account | Was anlegen | Umgebungsvariable |
|---|---|---|---|
| 1 | **Google Cloud** (console.cloud.google.com) | Projekt → „APIs & Dienste“ → **Places API (New)** und **PageSpeed Insights API** aktivieren → „Anmeldedaten“ → API-Schlüssel. Empfohlen: zwei Keys, jeweils auf eine API beschränkt. Abrechnungskonto nötig (Places kostet, 200 $/Monat Guthaben entfallen seit 2025 – stattdessen 10.000 kostenlose Calls/Monat je SKU-Gruppe). | `GOOGLE_PLACES_API_KEY`, `PAGESPEED_API_KEY` |
| 2 | **Anthropic** (console.anthropic.com) | API-Key, Guthaben 5–10 € laden, Spend-Limit setzen | `ANTHROPIC_API_KEY` |
| 3 | **Cloudflare** (dash.cloudflare.com) | Account-ID kopieren; „My Profile → API Tokens → Create Token → Edit Cloudflare Workers/Pages“ (Account-Scope). Danach Pages-Projekt anlegen: `npx wrangler pages project create relaunch-previews --production-branch main` | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_PAGES_PROJECT` |
| 4 | **Supabase** (supabase.com) | **Neues** Projekt (nicht das der App), Region eu-central. „Connect“ → Connection string **Transaction pooler** (Port 6543) kopieren, Passwort einsetzen | `DATABASE_URL` |
| 5 | **Instantly** (instantly.ai) | Plan Growth (ab 30 Mails/Tag) bzw. Hypergrowth (ab ~100/Tag). Postfächer verbinden, Warm-up an. Kampagne anlegen mit 3 Schritten: Schritt 1 Betreff `{{subject}}` Text `{{body_1}}`; Schritt 2 nach 3 Tagen `{{subject_fu}}` / `{{body_2}}`; Schritt 3 nach 4 weiteren Tagen `{{subject_fu}}` / `{{body_3}}`. „Stop on reply“ an. Settings → Integrations → API Key (v2). Kampagnen-ID aus der URL | `INSTANTLY_API_KEY`, `INSTANTLY_CAMPAIGN_ID`, `SENDER_BACKEND=instantly` |
| 6 | **MillionVerifier** (optional) | API-Key, 10.000 Credits ≈ 3 € | `MILLIONVERIFIER_API_KEY` |
| 7 | **Resend** (optional, Tagesbericht) | Domain verifizieren (eine Berichts-Subdomain, nie die Antwortadresse), API-Key | `RESEND_API_KEY`, `REPORT_EMAIL_FROM`, `REPORT_EMAIL_TO` |

Alle Variablen mit Erklärung: **`.env.example`**. Lokal nach `.env` kopieren.

### 2.2 GitHub Actions einrichten

1. Repo → **Settings → Secrets and variables → Actions**.
2. **Secrets:** `DATABASE_URL`, `GOOGLE_PLACES_API_KEY`, `PAGESPEED_API_KEY`, `ANTHROPIC_API_KEY`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `INSTANTLY_API_KEY`, `INSTANTLY_CAMPAIGN_ID`, optional `MILLIONVERIFIER_API_KEY`, `RESEND_API_KEY`.
3. **Variables** (nicht geheim): `SENDER_NAME`, `SENDER_TITLE`, `SENDER_ADDRESS`, `SENDER_PHONE`, `PREVIEW_DOMAIN`, `SENDER_BACKEND` (`dryrun` → später `instantly`), `AUTO_APPROVE` (`false`), `REPORT_EMAIL_TO`, `REPORT_EMAIL_FROM`, optional `DAILY_SEND_LIMIT_START`/`_MAX`.
4. Workflow `.github/workflows/relaunch-pipeline.yml` läuft Mo–Fr 07:40 und 12:40 UTC. Manuell: Actions → relaunch-pipeline → „Run workflow“ mit Stufe und Limit.
5. Ergebnisse: Job-Summary (Kurzbericht), Artefakte (Screenshots, Outbox, `run-summary.json`), Logs als JSON-Zeilen.
6. Review bleibt lokal: `git pull` ist nicht nötig, die Review-UI spricht direkt mit der Supabase-DB (`DATABASE_URL` in deiner lokalen `.env`). Screenshots für die UI holst du dir aus dem Actions-Artefakt in `screenshots/` oder lässt `pipeline run --stage screenshots` lokal laufen.

Hinweis privates Repo: ein Lauf braucht ca. 10–15 Minuten, zwei Läufe/Tag ≈ 600 Minuten/Monat, Free-Kontingent 2.000.

### 2.3 Domain-Setup

**1 Hauptdomain** (z. B. `seitenwechsel.de`):
- `preview.seitenwechsel.de` → Cloudflare Pages Custom Domain für das Projekt `relaunch-previews` (= `PREVIEW_DOMAIN`).
- Kundenseiten laufen später als eigene Pages-Projekte unter der Kundendomain; `promote` gibt die DNS-Anleitung aus (MX wird nie angefasst).
- Diese Domain **nie** zum Versand nutzen (Reputation schützen).

**2–3 Versanddomains** (z. B. `seitenwechsel-web.de`, `seitenwechsel.digital`, `sw-webdesign.de`), je 2–3 Postfächer (Google Workspace 6 €/Postfach oder Instantly-eigene Postfächer):
1. Domain bei Cloudflare/IONOS kaufen, in Instantly bzw. Google Workspace einrichten.
2. DNS je Versanddomain: **SPF** `v=spf1 include:_spf.google.com ~all` (bzw. Anbieter-Include), **DKIM** (Schlüssel aus Workspace/Instantly), **DMARC** `_dmarc TXT v=DMARC1; p=quarantine; rua=mailto:dmarc@<versanddomain>`, dazu Custom-Tracking-Domain von Instantly (CNAME).
3. Weiterleitung einrichten: in jedem Postfach alle eingehenden Mails an **auguyoga@gmail.com** weiterleiten (Gmail: Einstellungen → Weiterleitung; Workspace: Routing). Zusätzlich im Sequencer `Reply-To` setzen – die Pipeline setzt `REPLY_TO_EMAIL` ohnehin als Reply-To.
4. **Warm-up 2–3 Wochen** in Instantly laufen lassen, bevor `SENDER_BACKEND=instantly` aktiv wird. Start 30 Mails/Tag über alle Postfächer, Rampe +20/Woche bis 150 (`DAILY_SEND_LIMIT_*`).
5. Faustregel: max. 30–40 Mails pro Postfach und Tag inkl. Follow-ups → 150 Leads/Tag brauchen ca. 10–12 Postfächer auf 4–5 Domains.

### 2.4 Geschätzte Monatskosten

Annahmen: 22 Versandtage, 3 Mails je Lead, Funnel ≈ 1 versendet je 3 entdeckte Betriebe, Haiku 5.5 ≈ 0,003 € je generierte Preview.

| Posten | 30 Mails/Tag | 100 Mails/Tag | 150 Mails/Tag |
|---|---|---|---|
| Instantly (Growth / Hypergrowth) | 35 € | 90 € | 90 € |
| Postfächer (Google Workspace, 6 €) | 3 × 6 = 18 € | 8 × 6 = 48 € | 12 × 6 = 72 € |
| Versanddomains (≈ 1 €/Monat) | 3 € | 4 € | 5 € |
| Google Places (≈ 0,03 €/Request, 20 Treffer) | 3 € | 10 € | 15 € |
| PageSpeed Insights | 0 € | 0 € | 0 € |
| Anthropic (Haiku 5.5) | 2 € | 7 € | 10 € |
| MillionVerifier (0,30 €/1.000) | 1 € | 2 € | 3 € |
| Cloudflare Pages, Supabase, GitHub Actions | 0 € | 0 € | 0 € |
| Hauptdomain | 1 € | 1 € | 1 € |
| **Summe** | **≈ 65 €** | **≈ 160 €** | **≈ 195 €** |

Bei 150/Tag ist **nicht Geld, sondern Lead-Vorrat der Engpass**: NRW hat grob 1.500–2.000 Fahrschulen, davon vielleicht 40 % mit messbar schlechter Website → ~700 Leads. Rechtzeitig weitere Bundesländer (`REGION_CITIES_FILE`) oder eine zweite Branche einplanen.

### 2.5 Täglicher Ablauf für dich (10–20 Minuten)

1. **Morgens:** Actions-Lauf im Summary prüfen (Fehler? Kosten?).
2. **Review:** `pipeline review` → Leads in `pending_review` durchgehen: Vorher/Nachher ansehen, Befunde und Validator-Warnungen lesen, Mail ggf. anpassen, **Freigeben** oder **Ablehnen**. „Alle ohne Warnungen freigeben“ für die Sammel-Freigabe. Der Mittagslauf (12:40 UTC) versendet die Freigaben im Zeitfenster.
3. **Antworten** in Gmail bearbeiten: Interesse → kurzes Telefonat/Angebot; Absage → kommt automatisch beim nächsten Sync auf die Sperrliste (negative Antwort) – zusätzlich jederzeit `pipeline block adresse@x.de`.
4. **Abschluss:** Inhalte ggf. in `customers/<name>/site.json` korrigieren, `pipeline promote <lead> --domain kundendomain.de`, DNS-Anleitung an den Kunden, Domain verbinden.
5. **Wöchentlich:** `pipeline report --days 7`, Bounce-Rate in Instantly (< 3 %), Mail-Vorlagen anhand der Antworten nachschärfen.

---

## 3. Branchen erweitern

```
industries/<neue-branche>/
  industry.yaml        Suchbegriffe ("Physiotherapie in {city}"), Seitentypen, Scoring-Zusätze, Prompt-Hinweise
  email/initial.md, followup_1.md, followup_2.md, footer.md   (Variablen siehe industries/fahrschulen/email/README.md)
  site/Template.astro  rendert das generische Content-Schema (services/prices/hours/team/contact/about)
  site/images/ + LICENSES.md
```
Dann `INDUSTRY=<neue-branche>` setzen. Das Content-Schema (`pipeline/schema.py`) ist branchenneutral; die Beschriftung macht das Template.

## 4. Schutz vor erfundenen Inhalten

- Das LLM füllt nur ein striktes JSON-Schema (pydantic, `additionalProperties: false`), schreibt nie HTML.
- Jedes Faktenfeld (Name, Preis, Zeit, Telefon, Klasse) trägt `source` (URL) und `snippet`.
- `pipeline/validator.py` prüft jede Zahl, Uhrzeit, Telefonnummer, jeden Namen und typische Werbe-Behauptungen gegen den extrahierten Quelltext. Verstöße erscheinen als Warnung im Review; `AUTO_APPROVE` gibt nur warnungsfreie Leads frei.
- Fehlende Daten bleiben `null`/leer → Sektion wird nicht gerendert (z. B. keine Preise bei „Rote Ampel“ in der Demo).
- Bilder nur von der eigenen Domain des Betriebs (vermessen, ≥ 900 px) oder aus dem lizenzierten Set. Nie aus Google Maps.

## 5. Qualität der Previews

Lighthouse (mobil, Demo-Preview, lokal gemessen): **Performance 100, Barrierefreiheit 95–100, Best Practices 96–100**.
SEO zeigt bei Previews absichtlich 66 („blocked from indexing“ durch noindex); bei per `promote` erzeugten
Kundenseiten entfällt noindex. Kein JavaScript, selbst gehostete Schrift, keine externen Requests.

## 6. Tests

```bash
python -m pytest -q        # 30 Tests: Extraktion, Scoring, Schema, Validator, Sperrliste, Versandregeln, End-to-End-Demo
```
Der E2E-Test baut die Astro-Site und macht Screenshots, wenn Node und Playwright vorhanden sind (sonst wird dieser Teil übersprungen).

## 7. Markenname und Domain – 5 Vorschläge

| Name | Domain-Ideen | Warum |
|---|---|---|
| **Seitenwechsel** | seitenwechsel-web.de, seitenwechsel.digital | Doppeldeutig (Website-Wechsel), merkfähig, deutsch |
| **Klarseite** | klarseite.de, klarseite.digital | Versprechen „klar, lesbar, modern“ |
| **Neuseite** | neuseite.de, neuseite.io | Sagt genau, was man bekommt |
| **Webfrisch** | webfrisch.de | Freundlich, handwerklich, passt zu lokalen Betrieben |
| **Ortsseite** | ortsseite.de | Positionierung: Websites für Betriebe vor Ort |

Verfügbarkeit offline nicht geprüft. Empfehlung: Hauptdomain `.de`, Versanddomains als Varianten (`-web.de`, `.digital`).

## 8. Was August noch tun muss

Priorisierte Go-live-Checkliste: **[docs/GO-LIVE.md](docs/GO-LIVE.md)**. Entscheidungen mit Begründung: **[docs/DECISIONS.md](docs/DECISIONS.md)**.
