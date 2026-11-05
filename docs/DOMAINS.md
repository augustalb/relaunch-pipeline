# Domain-Plan: Diaktoros

Stand: 05.11.2026. Die vier Domains stammen aus einem beendeten Projekt (Vertrieb für Cybersecurity) und werden
für die Relaunch-Pipeline umgewidmet. Registrar und DNS: Squarespace. Alle vier laufen am **09.02.2027** ab,
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
2. **Google Workspace neu buchen** mit drei Postfächern, eines je Versanddomain, Namen wie eine echte Person
   (z. B. `august@diaktoros-growth.de`). Die Versanddomains als zusätzliche Domains hinzufügen.
   `diaktoros.de` ebenfalls hinzufügen, aber **ohne eigenes Postfach**: `info@` und `admin@diaktoros.de` als
   kostenlose Aliasse an ein vorhandenes Postfach hängen.
3. **DKIM erneuern.** In der Admin-Konsole je Domain einen neuen Schlüssel erzeugen (Apps → Gmail →
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
| Google Workspace, 3 Postfächer | 20–25 € |
| Instantly Growth | 35 € |
| Domains (Verlängerung auf den Monat umgelegt) | 5 € |
