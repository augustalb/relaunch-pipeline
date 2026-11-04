# E-Mail-Vorlagen (Fahrschulen)

Reiner Text, Markdown nur als Dateiformat. Jede Datei:

```
subject: Betreffzeile mit {variablen}
---variant---
Text Variante A
---variant---
Text Variante B (optional, beliebig viele)
```

Die Variante wird pro Empfänger deterministisch gewählt (Hash der Lead-ID), damit nicht alle
Mails identisch sind. `footer.md` wird automatisch unter jede Mail gehängt.

Verfügbare Variablen:

| Variable | Inhalt |
|---|---|
| `{anrede}` | „Sehr geehrter Herr Müller" oder neutral „Guten Tag" |
| `{firma}` | Firmenname aus dem Impressum |
| `{stadt}` | Stadt aus der Discovery |
| `{befund_1}`, `{befund_2}`, `{befund_3}` | Messbare Befunde als Sätze (fehlende Befunde werden leer) |
| `{preview_url}` | Link zur Preview (der einzige Link in der Mail) |
| `{sender_name}`, `{sender_title}`, `{sender_address}`, `{sender_phone}` | aus der Config |

Regeln aus der Spezifikation: unter 120 Wörter, genau ein Link, keine Bilder/Anhänge, weiche
Handlungsaufforderung. `pipeline` prüft Wortzahl und Linkanzahl beim Rendern und warnt im Review.
