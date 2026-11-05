# Was August noch tun muss – Go-live-Checkliste (priorisiert)

Reihenfolge = Priorität. Alles bis Punkt 7 ist nötig, bevor die erste echte Mail rausgeht.

1. **Absenderdaten eintragen** (`SENDER_NAME`, `SENDER_ADDRESS`, `SENDER_TITLE`, `SENDER_PHONE`) – Pflicht fürs Impressum in der Mail (§ 5 DDG/UWG).
2. **Rechtliche Absicherung Kaltakquise prüfen – vor dem ersten Versand.** Werbung per E-Mail braucht nach § 7 Abs. 2 Nr. 2 UWG grundsätzlich eine vorherige ausdrückliche Einwilligung, auch gegenüber Unternehmen. Die „mutmaßliche Einwilligung“ genügt nur für Werbeanrufe bei Unternehmen, nicht für E-Mails. Abmahnrisiko. Eingebaut sind: konkreter Bezug zur Website, Abmeldesatz, Sperrliste. Das ersetzt keine Einwilligung. Empfehlung: vor dem Start mit einem Anwalt oder der IHK sprechen; Alternative ist der Brief-Kanal (Punkt 11).
3. **Domains und Postfächer** – Plan steht in **[DOMAINS.md](DOMAINS.md)**: `diaktoros.de` als Hauptdomain, `diaktoros-growth.de`, `diaktoros-growth.com`, `diaktoros-pipeline.com` als Versanddomains (vorhanden, DNS eingerichtet). Offen: Markenseite umbauen, Google Workspace neu buchen, DKIM erneuern, Weiterleitung an auguyoga@gmail.com. **Warm-up neu starten – dauert 2–3 Wochen**, deshalb früh.
4. **Accounts anlegen und Keys eintragen:** Google Cloud (Places API New + PageSpeed), Anthropic, Cloudflare (Pages-Token + Account-ID), Supabase (neues Projekt → `DATABASE_URL`), Instantly (Kampagne mit 3 Schritten `{{body_1}}` … anlegen → `INSTANTLY_CAMPAIGN_ID`), optional MillionVerifier, optional Resend.
5. **Cloudflare Pages Projekt** `relaunch-previews` anlegen (`npx wrangler pages project create relaunch-previews`) und die Preview-Domain als Custom Domain verbinden.
6. **GitHub:** Secrets + Variables setzen (Liste im README), Workflow einmal manuell mit `stage=discovery, limit=5` starten, dann `scoring`, `contact` … Stufe für Stufe prüfen. Erst wenn alles sauber läuft: `SENDER_BACKEND=instantly`.
7. **Erste 10 Leads von Hand reviewen** (`pipeline review`), Mails ggf. in `industries/fahrschulen/email/*.md` nachschärfen. `AUTO_APPROVE` erst nach ~50 sauberen Reviews einschalten.
8. **Preise/Angebot vorbereiten:** Was passiert nach der Antwort? Kurzes Angebots-PDF oder E-Mail-Vorlage (390 € Setup, 30 €/Monat), AGB/Vertrag für Hosting + Support.
9. **Rechtstexte für Kundenseiten:** Beim `promote` muss der Kunde eigenes Impressum/Datenschutz liefern (aktuell wird auf die alten Seiten verlinkt).
10. **Monitoring:** GitHub-Actions-Mail bei fehlgeschlagenem Lauf aktivieren; wöchentlich `pipeline report --days 7` lesen; Bounce-Rate in Instantly < 3 % halten.
11. **Später:** zweite Branche als Ordner anlegen (z. B. Physiotherapie, Dachdecker), Brief-Kanal (`LetterSender`), Checkout.
