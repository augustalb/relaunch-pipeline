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

## Veröffentlichen (Cloudflare Workers, mit GitHub verbunden)

Das Projekt `diaktoros-site` in Cloudflare ist mit diesem Repository verbunden. Jeder Push auf `main` veröffentlicht neu.

Einstellungen unter Settings → Build:

| Feld | Wert |
|---|---|
| Root directory | `brand-site` |
| Build command | leer |
| Deploy command | `npx wrangler deploy` |

`wrangler.jsonc` legt fest, dass nur dieser Ordner als statische Seite hochgeladen wird; `.assetsignore` hält Konfiguration und README raus.

Eigene Domain: Für `diaktoros.de` muss die Domain ihre DNS bei Cloudflare haben („Add a domain“, Free-Plan).
**Vor dem Umstellen der Nameserver bei Squarespace prüfen, dass MX, SPF, DKIM (`google._domainkey`) und DMARC übernommen wurden.**
Danach im Worker unter Settings → Domains & Routes `diaktoros.de` und `www.diaktoros.de` als Custom Domain hinzufügen.
`preview.diaktoros.de` gehört zum separaten Pages-Projekt `relaunch-previews` der Pipeline.
