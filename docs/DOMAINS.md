# Domain-Plan: Diaktoros

Stand: 05.11.2026. Die vier Domains stammen aus einem beendeten Projekt (Vertrieb für Cybersecurity) und werden
für die Relaunch-Pipeline umgewidmet. Registrar: Squarespace. DNS: `diaktoros.de` seit 06.11.2026 bei Cloudflare, die drei Versanddomains weiter bei Squarespace. Alle vier laufen am **09.02.2027** ab,
Verlängerung rechtzeitig prüfen.

## Rollen

| Domain | Rolle | Wird von ihr versendet? |
|---|---|---|
| `diaktoros.de` | Hauptdomain: Markenseite + Previews unter `preview.diaktoros.de` | **nein, nie** |
| `diaktoros-growth.de` | Versanddomain | ja |
| `diaktoros-growth.com` | Versanddomain | ja |
| `diaktoros-pipeline.com` | Versanddomain | ja |

Die drei Versanddomains leiten im Browser bereits auf `diaktoros.de` weiter. Das bleibt so: Wer den Absender
nachschlägt, landet auf der Markenseite.

## Geprüfter Ist-Zustand (05.11.2026, öffentliches DNS)

- SPF (`include:_spf.google.com`), DKIM (`google._domainkey`), DMARC (`p=quarantine`) und MX (Google) sind bei allen vier gesetzt.
- Keine Domain steht auf Spamhaus DBL oder SURBL.
- Google Workspace ist gekündigt: Es gibt keine Postfächer mehr, eingehende Mails an diese Domains kommen nicht an.
- Der DKIM-Eintrag gehört zum alten Workspace und muss nach der Neueinrichtung ersetzt werden.
- DMARC-Berichte gehen an `admin@diaktoros.de`, das Postfach existiert nicht mehr.
- Die Aufwärmung von vor ca. 9 Monaten zählt nicht mehr. Vorteil bleibt das Alter der Domains.

## Schritte

1. **Markenseite `diaktoros.de` umbauen.** Die Seite beschreibt noch Vertrieb für Cybersecurity. Neu: kurze
   Seite „Neue Websites für Fahrschulen“ mit Impressum und Datenschutz. Muss fertig sein, **bevor** die erste Mail rausgeht.
2. **Google Workspace neu buchen** (Business Starter), Registrierung mit `diaktoros.de` als Hauptdomain.
   Vier Postfächer:

   | Postfach | Aufgabe |
   |---|---|
   | `august@diaktoros.de` | Hauptkonto/Admin, **versendet nie Kaltmails**; `info@` und `admin@diaktoros.de` als Aliasse |
   | `a.albrecht@diaktoros-growth.de` | Versand |
   | `august@diaktoros-growth.com` | Versand |
   | `albrecht@diaktoros-pipeline.com` | Versand |

   Versanddomains als **sekundäre Domains** hinzufügen (nicht als Alias-Domain). Admin getrennt vom Versand,
   damit eine Sperre eines Versandpostfachs nicht den Zugang zur Admin-Konsole kostet.
   Meldet Google die Domain als belegt, hängt sie noch am alten gekündigten Konto: dort reaktivieren oder löschen.
3. **DKIM erneuern.** In der Admin-Konsole für alle vier Domains einen neuen Schlüssel erzeugen (Apps → Gmail →
   E-Mails authentifizieren) und den TXT-Eintrag `google._domainkey` bei Squarespace ersetzen. Danach „Authentifizierung starten“.
4. **Weiterleitung** aller eingehenden Mails an `auguyoga@gmail.com` (Admin-Konsole → Gmail → Routing).
5. **Instantly:** die drei Postfächer verbinden, Warm-up an, Custom-Tracking-Domain je Versanddomain (CNAME bei Squarespace).
   **2–3 Wochen** aufwärmen, erst dann `SENDER_BACKEND=instantly`.
6. **Preview-Domain:** im Cloudflare-Pages-Projekt `relaunch-previews` die Custom Domain `preview.diaktoros.de`
   hinzufügen und den angezeigten CNAME bei Squarespace eintragen. Die Markenseite selbst bleibt davon unberührt.
7. **GitHub-Variablen:** `PREVIEW_DOMAIN=preview.diaktoros.de`, `BRAND_NAME=Diaktoros`, dazu die Absenderdaten.

## Kosten (Start mit 30 Mails/Tag)

| Posten | ca. pro Monat |
|---|---|
| Google Workspace, 4 Postfächer (1 Admin + 3 Versand) | 28–32 € |
| Instantly Growth | 35 € |
| Domains (Verlängerung auf den Monat umgelegt) | 5 € |
