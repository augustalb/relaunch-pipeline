# Entscheidungen

Format je Eintrag: Kontext → Wahl → Begründung → Alternativen.

## 1. Repository-Struktur: eigenständiges Repo `augustalb/relaunch-pipeline`
- **Kontext:** Das Projekt hat nichts mit anderen Produkten zu tun und braucht eigene Secrets, Workflows und Historie.
- **Wahl:** Eigenes Repo, Python-Paket und Astro-Site im Wurzelverzeichnis, Workflows unter `.github/workflows/`.
- **Begründung:** Saubere Trennung von Secrets, Actions-Minuten, Issues und Zugriffsrechten; die tägliche Pipeline läuft unabhängig.
- **Alternativen:** Unterordner in einem bestehenden Repo (verworfen: vermischt fremde Projekte), Monorepo-Tooling (übertrieben).

## 2. Sprache/Stack: Python 3.11+ (Pipeline) und Astro 5 + Tailwind 4 (Sites)
- **Wahl:** Wie vorgegeben. Python-Pakete: httpx, BeautifulSoup/lxml, pydantic 2, SQLAlchemy 2, typer, FastAPI, Playwright, anthropic.
- **Begründung:** Beste Bibliotheken für Crawling/Validierung; Astro erzeugt statisches HTML ohne JS-Ballast (Lighthouse ≥ 90 einfach erreichbar).
- **Alternativen:** Node für alles (weniger reife Crawling-Tools), Next.js (unnötige Laufzeit).

## 3. Datenbank: SQLAlchemy mit SQLite lokal, Supabase Postgres (Free Tier) in Produktion
- **Kontext:** Läuft täglich in GitHub Actions ohne Laptop; braucht einen persistenten Zustand.
- **Wahl:** Ein ORM-Codepfad, `DATABASE_URL` entscheidet. Produktion: neues Supabase-Projekt (nicht das der App), Pooler-URL (Port 6543) für kurze Actions-Verbindungen.
- **Begründung:** Kostenlos, verlässlich, keine Datei-Artefakte in Actions nötig. Der tägliche Lauf hält das Free-Tier-Projekt aktiv (Pausierung erst nach 7 Tagen Inaktivität).
- **Alternativen:** SQLite als Actions-Artefakt/Commit (fragil, Race Conditions), Neon (gleichwertig, kein bestehender Account), Turso.

## 4. Scheduling: GitHub Actions Cron (Mo–Fr 07:40 und 12:40 UTC)
- **Wahl:** Zwei Läufe pro Werktag: morgens voller Lauf, mittags Sync + Versand (Nachzügler aus dem Review).
- **Begründung:** 0 € (öffentliches Repo) bzw. im Free-Kontingent (privates Repo: 2.000 min/Monat, ein Lauf ≈ 10–15 min → ~600 min/Monat). Logs, Artefakte (Screenshots, Outbox) und Secrets sind eingebaut.
- **Alternativen:** Fly.io/Render-Cron (Kosten, mehr Setup), Supabase pg_cron + Edge Functions (kein Playwright/Node-Build möglich), eigener VPS (Wartung).

## 5. LLM: Anthropic `claude-haiku-5-5` als Default, Structured Outputs, Effort `low`
- **Kontext:** Auftrag: „nimm das günstigste, das die Qualität schafft“. Die Aufgabe ist Extraktion/Umformulierung in ein striktes Schema, kein kreatives Schreiben.
- **Wahl:** Haiku 5.5 (0,10 $/MTok Input, 0,50 $/MTok Output), `output_config.format = json_schema` aus dem pydantic-Modell, Prompt-Caching für den System-Prompt. Umschaltbar per `LLM_MODEL` (z. B. `claude-sonnet-5-5`).
- **Begründung:** ≈ 0,003 € pro Lead; der Validator fängt erfundene Fakten unabhängig vom Modell. Das LLM schreibt nie HTML.
- **Alternativen:** Sonnet 5.5 (10–20× teurer, bessere Texte – bei Review-Beschwerden umschalten), Opus (unnötig), lokale Modelle (Infrastruktur).
- **Ohne Key:** deterministischer „Composer“ baut dieselbe Struktur aus den Regex-Kandidaten. Dadurch läuft die Demo offline und es gibt einen Fallback, falls das LLM zweimal die Validierung reißt.

## 6. Schutz gegen erfundene Inhalte: `Sourced`-Felder + regelbasierter Validator
- **Wahl:** Jedes Faktenfeld trägt `value/source/snippet`. `pipeline/validator.py` prüft jede Zahl, Uhrzeit, Telefonnummer, jeden Namen/Klassennamen und typische Marketing-Behauptungen („seit 1985“, „Testsieger“, „98 % Bestehensquote“) gegen den Quelltext (inkl. entschleierter E-Mails).
- **Begründung:** Modellunabhängig, erklärbar im Review (deutscher Satz pro Verstoß), testbar.
- **Alternativen:** LLM-as-a-judge (teurer, selbst halluzinationsanfällig), nur Schema-Validierung (reicht nicht).

## 7. Branchenpakete als Ordner (`industries/<name>/`)
- **Wahl:** `industry.yaml` (Suchbegriffe, Seitentypen, Scoring-Zusätze, Prompt-Hinweise), `email/*.md`, `site/Template.astro`, `site/images/` + `LICENSES.md`. Das Astro-Template wird direkt aus dem Branchenordner importiert (`import.meta.glob`), Tailwind scannt den Ordner per `@source`.
- **Begründung:** Neue Branche = neuer Ordner, kein Python/JS-Code anfassen. Das Content-Schema ist generisch („services“ statt „Führerscheinklassen“), die Beschriftung kommt aus dem Template.
- **Alternativen:** Branchenspezifische pydantic-Modelle (würde Code pro Branche erfordern).

## 8. Discovery: Google Places API (New) Text Search mit Field Mask, ToS-konforme Speicherung
- **Wahl:** `places:searchText`, Felder id/displayName/formattedAddress/nationalPhoneNumber/websiteUri/rating/userRatingCount/businessStatus. Dauerhaft nur `place_id`; die übrigen Places-Felder bekommen `places_cached_at` und werden nach 30 Tagen genullt (`housekeeping.scrub_places_cache`). Firmenname, Adresse und Telefon für die Website kommen aus dem Impressum des Betriebs, nicht aus Places.
- **Begründung:** Google Maps Platform ToS (3.2.3/3.2.4): Place-ID unbegrenzt, andere Inhalte max. 30 Tage cachen. Kostenbremse `PLACES_MAX_REQUESTS_PER_RUN`.
- **Ausschlüsse:** keine Website, dauerhaft geschlossen, Fremdplattformen (`config/platform_domains.txt`), Ketten (`config/blocklist_domains.txt` + Heuristik ≥ 3 Standorte gleiche Domain), Sperrliste.
- **Alternativen:** Scraping von Branchenportalen (rechtlich heikel, instabil), OpenStreetMap (schlechte Website-Abdeckung), Places Legacy API (wird eingestellt).

## 9. Scoring: PageSpeed Insights (mobil) + eigene Checks → Score 0–100, Schwelle 55
- **Wahl:** Punkte je nachweisbarem Mangel (kein HTTPS 18, kein viewport 22, Tabellen-Layout 14, PSI < 50 → 20, LCP ≥ 4 s → 8/14, Copyright-Jahr, Baukasten, kaputte Unterseiten …). Befunde sind deutsche Sätze mit der gemessenen Zahl.
- **Begründung:** Die Mail darf nur Gemessenes behaupten; jede Zahl im Befund ist reproduzierbar (PSI-Link, Browser). Die moderne Kontroll-Fixture liegt bei 18 Punkten, die schlechten bei 82–100.
- **Alternativen:** Nur Lighthouse (verpasst Tabellen-Layouts, alte Jahreszahlen), ML-Scoring (nicht erklärbar).

## 10. Versand: Instantly API v2 hinter `Sender`-Interface; `DryRunSender` als Default
- **Wahl:** Lead wird mit fertig gerenderten Texten als Custom Variables (`subject`, `body_1..3`) in eine Instantly-Kampagne geschoben. Warm-up, Postfach-Rotation, Zeitplan, Follow-ups und Stop-on-Reply macht Instantly. Status-Sync liest Antworten/Bounces/Interest-Status zurück.
- **Begründung:** Zustellbarkeit ist das größte Risiko bei Kaltakquise; eigene SMTP-Rotation ist Zeitverschwendung und endet im Spam-Ordner. Instantly (ab ≈ 30 €/Monat, unbegrenzt Postfächer) ist die günstigste etablierte Option mit brauchbarer API; die Texte bleiben trotzdem im Repo versioniert.
- **Alternativen:** Smartlead (ähnlich, API minimal teurer), lemlist (teurer), Resend/SES (kein Warm-up, keine Rotation → nein), eigenes SMTP (nein).
- **Hinweis:** Die Instantly-Endpunkte (`/leads`, `/emails`, `/leads/list`) sind nach öffentlicher Doku implementiert, aber ohne Key ungetestet → erster Lauf mit `--limit 1` prüfen.
- **Brief-Kanal:** `OutboundMessage.channel` kennt bereits `"letter"`; ein `LetterSender` implementiert nur `send()`/`sync()`.

## 11. Previews: ein Cloudflare-Pages-Projekt, `wrangler pages deploy` per Direct Upload
- **Wahl:** Alle aktiven Previews werden bei jedem Lauf komplett neu gebaut und als ein Deployment hochgeladen (`/{slug}/`). Slug = Firmenname + 6 Hex-Zeichen. noindex per Meta, `robots.txt` und `_headers` (X-Robots-Tag). Ablauf nach 45 Tagen = JSON löschen + neu deployen.
- **Begründung:** Kostenlos (Pages Free: 500 Builds/Monat, unbegrenzte Sites), Custom Domain mit SSL, keine Build-Minuten bei Direct Upload. Ein Projekt statt eines pro Lead vermeidet Limits.
- **Alternativen:** Netlify (ähnlich, striktere Free-Limits), GitHub Pages (kein noindex-Header, öffentlich im Repo), Vercel (Hobby verbietet kommerzielle Nutzung).

## 12. Design-Entscheidungen Template Fahrschulen
- Mobile-first One-Pager mit sticky Header + Anruf-Button, Hero mit Bild + „Direkt erreichbar“-Karte (Telefon, Adresse, erste Zeiten), Klassen als Karten mit Badge/Preis, Preise als Liste, Zeiten, Team (Initialen statt Fotos – keine fremden Bilder), Über uns, Kontakt, Footer mit Links zu Impressum/Datenschutz der alten Seite.
- 6 Farbpaletten, deterministisch per Slug gewählt → Previews sehen nicht alle gleich aus. Schrift Manrope (OFL, selbst gehostet – keine Google-Fonts-Einbindung wegen DSGVO/LG München).
- Kein JavaScript auf der Seite, keine externen Requests außer Bildern der eigenen Domain → Lighthouse-Performance unkritisch.
- Hero-Bild: eigenes Bild des Betriebs, wenn ≥ 1200 px breit (wird beim Extrahieren vermessen), sonst eines von vier Unsplash-Fotos (`industries/fahrschulen/site/images/LICENSES.md`).

## 13. Review: lokale FastAPI-App, Freigabe per Status-Übergang, `AUTO_APPROVE` nur ohne Warnungen
- **Begründung:** Keine Auth nötig (läuft nur auf 127.0.0.1), Screenshots und lokaler Preview-Build werden direkt ausgeliefert. Sammel-Freigabe betrifft bewusst nur warnungsfreie Leads.

## 14. E-Mail-Adressen: ohne Verifizierungsdienst kein Versand (`REQUIRE_VERIFIED_EMAIL=true`)
- **Begründung:** Bounces > 3 % ruinieren die Versanddomain. MillionVerifier (≈ 0,30 €/1.000) ist über Interface angebunden; im Dry-Run wird die Regel ignoriert, bei Instantly nicht.
- **Alternative:** Instantly-eigene Verifizierung (teurer je Adresse), ZeroBounce (teurer).

## 15. Operator-Bericht per Resend (optional)
- **Kontext:** Antworten laufen ausschließlich *an* auguyoga@gmail.com; diese Adresse darf nie senden.
- **Wahl:** Bericht im CLI, im GitHub-Step-Summary und optional per Resend (3.000 Mails/Monat gratis) von einer separaten Berichts-Domain.
- **Alternativen:** Über den Sequencer (nicht dafür gedacht), SMTP von Gmail (verboten per Vorgabe).

## 16. Kostenlimits pro Lauf
- Places: `PLACES_MAX_REQUESTS_PER_RUN=60` (≈ 1,80 €), PSI: 100 Requests (kostenlos), LLM: `LLM_MAX_COST_PER_RUN_EUR=2`. Überschreiten → Stufe stoppt sauber, Rest läuft weiter; alles landet in der Tabelle `costs` und im Bericht.

## 17. Keine Preise in der Erstmail
- Vorgabe. Preise liegen nur in der Config (`SETUP_PRICE`, `MONTHLY_PRICE`) für spätere Angebots-Templates.
