"""Owner name / salutation extraction from German imprint pages."""

from __future__ import annotations

import re

from .util import collapse_ws

MALE = set(
    """Alexander Andreas Armin Axel Benjamin Bernd Bernhard Björn Carsten Christian Christoph Daniel David Dennis Dieter Dirk Dominik Eckhard Erik Fabian Felix Florian Frank Franz Georg Gerd Gerhard Günter Günther Hans Harald Heiko Heinz Helmut Holger Horst Ingo Jan Jens Joachim Jochen Johannes Jonas Jörg Josef Jürgen Kai Karl Karsten Kevin Klaus Lars Lukas Lutz Manfred Marcel Marco Mario Markus Martin Mathias Matthias Max Maximilian Michael Mike Moritz Nico Niklas Nils Norbert Olaf Oliver Patrick Paul Peter Philipp Rainer Ralf Reinhard Rene René Robert Roland Rolf Rüdiger Sascha Sebastian Siegfried Simon Stefan Steffen Stephan Sven Thomas Thorsten Tim Tobias Torsten Udo Ulrich Uwe Volker Walter Werner Wilhelm Wolfgang Ahmet Ali Mehmet Murat Mustafa Hakan Cem Emre Kemal Hasan Hüseyin Yusuf Ömer Tim Tom Timo Leon Luca Jakob Julian Jonathan Marc Mark Ben""".split()
)
FEMALE = set(
    """Andrea Angela Angelika Anja Anke Anna Anne Annette Astrid Barbara Bettina Birgit Brigitte Carola Carolin Christa Christiane Christina Christine Claudia Cornelia Dagmar Daniela Diana Doris Elke Elisabeth Erika Eva Franziska Gabi Gabriele Gisela Gudrun Hannelore Heike Helga Ilona Ines Inge Ingrid Irene Iris Jana Janina Jennifer Jessica Julia Jutta Karin Katharina Kathrin Katja Katrin Kerstin Kirsten Klaudia Laura Lena Lisa Manuela Maria Marion Martina Melanie Michaela Monika Nadine Nicole Nina Petra Regina Renate Rita Sabine Sabrina Sandra Sarah Silke Simone Sonja Stefanie Stephanie Susanne Sylvia Tanja Ulrike Ursula Ute Vanessa Vera Verena Yvonne Ayşe Aysche Fatma Elif Zeynep Emine Hatice Merve Leyla Sophie Sophia Marie Lea Hannah Emma Mia Lara""".split()
)

_LABELS = r"(?:inhaber(?:in)?|geschäftsführer(?:in)?|geschaeftsfuehrer(?:in)?|vertreten durch|vertretungsberechtigt(?:er|e)?(?: geschäftsführer(?:in)?)?|verantwortlich(?:er)?(?: i\.?s\.?d\.?| im sinne| für den inhalt)?[^:\n]{0,40}|betreiber(?:in)?|ansprechpartner(?:in)?)"
_WORD = r"[A-ZÄÖÜ][^\W\d_]+(?:-[A-ZÄÖÜ][^\W\d_]+)?"  # one capitalised (possibly hyphenated) name part
_NAME = rf"((?:(?:Herr|Frau|Dipl\.-Ing\.|Dr\.|Prof\.)[ \t]+)?{_WORD}(?:[ \t]+{_WORD}){{1,3}})"
_LABEL_NAME_RE = re.compile(r"(?i:" + _LABELS + r")[ \t]*:?[ \t]*\n?[ \t]*" + _NAME)
_TITLE_RE = re.compile(rf"\b(Herr|Frau)[ \t]+((?:Dr\.[ \t]+)?{_WORD}[ \t]+{_WORD})")
_STOPWORDS = {"Fahrschule", "GmbH", "UG", "Inhaber", "Impressum", "Kontakt", "Telefon", "Straße", "Strasse", "Angaben", "Gemäß", "Gemäss", "Umsatzsteuer", "Steuernummer", "Haftung", "Postfach"}


def extract_owner(text: str) -> tuple[str | None, str | None]:
    """Return (full_name, salutation) or (None, None).

    A salutation is only produced when the gender is unambiguous: an explicit
    "Herr"/"Frau" in the imprint, or a first name from the lists above.
    """
    text = text.replace("\xa0", " ")
    candidates: list[tuple[str, str | None]] = []  # (name, explicit title)
    for m in _TITLE_RE.finditer(text):
        candidates.append((collapse_ws(m.group(2)), m.group(1)))
    for m in _LABEL_NAME_RE.finditer(text):
        name = collapse_ws(m.group(1))
        title = None
        tm = re.match(r"(Herr|Frau)\s+(.*)", name)
        if tm:
            title, name = tm.group(1), tm.group(2)
        name = re.sub(r"^(Dipl\.-Ing\.|Dr\.|Prof\.)\s+", "", name)
        candidates.append((name, title))
    for name, title in candidates:
        parts = name.split()
        if len(parts) < 2 or any(p in _STOPWORDS for p in parts):
            continue
        first, last = parts[0], parts[-1]
        if title == "Herr" or (title is None and first in MALE and first not in FEMALE):
            return name, f"Sehr geehrter Herr {last}"
        if title == "Frau" or (title is None and first in FEMALE and first not in MALE):
            return name, f"Sehr geehrte Frau {last}"
        return name, None  # name known, gender ambiguous -> neutral salutation
    return None, None


def extract_company_name(text: str, fallback: str | None) -> str | None:
    """Company name from an imprint ("Fahrschule Müller GmbH") – first line mentioning the industry word."""
    for line in text.splitlines():
        line = collapse_ws(line)
        if 4 < len(line) < 70 and re.search(r"fahrschule", line, re.I) and not re.search(r"impressum|angaben gemäß|verantwortlich|@|www\.|http|tel", line, re.I):
            line = re.sub(r"^(angaben\s+gem[äa]+ß\s+§\s*5\s+(tmg|ddg)\s*:?\s*)", "", line, flags=re.I)
            return line.strip(" :-")
    return fallback
