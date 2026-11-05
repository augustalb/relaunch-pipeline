# Markenseite diaktoros.de

Statische Seite ohne Cookies, Tracking oder externe Requests. Nur ein kleines Inline-Skript für Einblend-Effekte und den Vorher-Nachher-Regler; ohne JavaScript bleibt alles lesbar. Schriften Manrope und Instrument Serif (beide OFL, Lizenzen in `assets/fonts/`) selbst gehostet.
Die Beispielbilder stammen aus dem Demo-Lauf mit der fiktiven „Fahrschule Müller“ (`docs/demo/`).

```
index.html            Startseite
impressum/index.html  Impressum
datenschutz/index.html Datenschutzerklärung
assets/               CSS, Schrift, Bilder
_headers, robots.txt  für Cloudflare Pages
```

## Vor dem Veröffentlichen ausfüllen

Alle Platzhalter sind gelb markiert und stehen in eckigen Klammern. Suchen: `class="ph"`.

- Impressum: vollständig. Eine USt-IdNr. nur ergänzen, falls Sie eine bekommen.
- Datenschutz: Löschfrist. Anbieterliste anpassen, falls ein Dienst wegfällt (z. B. MillionVerifier).
- **Beide Rechtstexte von Anwalt oder IHK prüfen lassen.** Sie sind ein Entwurf, keine Rechtsberatung.
- `info@diaktoros.de` muss erreichbar sein (Alias in Google Workspace, siehe `docs/DOMAINS.md`).
- Die Zusage „Antwort innerhalb von zwei Werktagen“ auf der Startseite nur stehen lassen, wenn sie stimmt.

## Lokal ansehen

```bash
python3 -m http.server 8811 -d brand-site
```
Dann http://127.0.0.1:8811 öffnen.

## Veröffentlichen (Cloudflare Pages)

1. Pages-Projekt anlegen und hochladen:
   `npx wrangler pages project create diaktoros-site --production-branch main`
   `npx wrangler pages deploy brand-site --project-name diaktoros-site`
2. Für die Hauptdomain `diaktoros.de` (ohne `www`) verlangt Cloudflare Pages, dass die Domain ihre DNS bei Cloudflare hat.
   Dafür in Cloudflare „Website hinzufügen“ (Free-Plan), Cloudflare übernimmt die vorhandenen Einträge.
   **Vor dem Umstellen prüfen, dass MX, SPF, DKIM und DMARC vollständig übernommen wurden**, dann bei Squarespace die Nameserver auf Cloudflare ändern.
3. Im Pages-Projekt `diaktoros.de` und `www.diaktoros.de` als Custom Domains hinzufügen.
   `preview.diaktoros.de` gehört zum anderen Projekt `relaunch-previews`.
