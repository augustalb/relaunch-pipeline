# Relaunch-Pipeline

Eigenständiges Projekt: automatisierte Akquise für Website-Relaunches lokaler Betriebe in Deutschland
(erste Branche Fahrschulen, Startregion NRW). Steht in keinem Zusammenhang mit anderen Projekten oder Apps.

Einstieg: **[README.de.md](README.de.md)**. Entscheidungen: **[docs/DECISIONS.md](docs/DECISIONS.md)**.
Go-live: **[docs/GO-LIVE.md](docs/GO-LIVE.md)**.

## Wichtigste Regel: keine claude.ai-Connectors
- **Für dieses Projekt niemals die nativen Connectors/MCP-Server von claude.ai benutzen** (Supabase, Gmail, Google Drive, Notion, Resend, Stripe, PostHog, Canva, Figma usw.). Sie gehören zu anderen Projekten des Betreibers. Auch keine Lesezugriffe.
- Zugriff auf Dienste dieses Projekts nur über eigene, projektbezogene Zugänge (Konten auf `august@diaktoros.de`), z. B. API-Schlüssel als GitHub-Secrets bzw. in einer eigenen Cloud-Umgebung für dieses Repository.

## Stack
- Python 3.11+ Paket `pipeline/` (CLI `pipeline`), SQLAlchemy (SQLite lokal, Supabase Postgres in Produktion)
- Astro 5 + Tailwind 4 in `site/`, Branchen-Templates in `industries/<branche>/site/Template.astro`
- Täglicher Lauf per GitHub Actions (`.github/workflows/relaunch-pipeline.yml`)

## Befehle
```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]" && python -m playwright install chromium
(cd site && npm ci)
python -m pytest -q
pipeline demo
```

## Konventionen
- Code und Kommentare Englisch, alles für den Betreiber (README, Checklisten, Mails, Site-Texte) Deutsch, Sie-Form.
- Neue Branche = neuer Ordner unter `industries/`, kein Code ändern.
- Keine erfundenen Fakten: Faktenfelder sind `Sourced`, `pipeline/validator.py` muss grün bleiben.
- Antwortadresse `REPLY_TO_EMAIL` ist nur Empfänger, es wird nie von ihr versendet.
- Nie echte Mails versenden, Geld ausgeben oder Accounts anlegen ohne ausdrückliche Freigabe.
