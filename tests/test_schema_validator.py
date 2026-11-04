import pytest
from pydantic import ValidationError

from pipeline.schema import Contact, HoursBlock, ServiceItem, SiteContent, Sourced, TeamMember, json_schema_for_llm
from pipeline.validator import validate_content

SOURCE = """### https://alt.de/
Fahrschule Müller Venloer Straße 212 50823 Köln Telefon: 0221 5509876
Klasse B – Pkw. Klasse A1. Grundgebühr Klasse B 299,00 € Fahrstunde 55,00 €
Bürozeiten Mo – Fr 15:00 – 18:30 Uhr. Inhaber: Hans-Peter Müller. info [at] alt [dot] de
"""


def _content(**over):
    base = dict(
        industry="fahrschulen",
        company_name=Sourced(value="Fahrschule Müller", source="https://alt.de/"),
        city="Köln",
        tagline="Ihre Fahrschule in Köln",
        hero_text="Fahrschule Müller in Köln.",
        services=[ServiceItem(name=Sourced(value="Klasse B", source="https://alt.de/"), price=Sourced(value="299,00 €", source="https://alt.de/"))],
        hours=[HoursBlock(label="Bürozeiten", entries=[Sourced(value="Mo – Fr 15:00 – 18:30 Uhr", source="https://alt.de/")])],
        team=[TeamMember(name=Sourced(value="Hans-Peter Müller", source="https://alt.de/"), role="Inhaber")],
        contact=Contact(phone=Sourced(value="0221 5509876", source="https://alt.de/"), email=Sourced(value="info@alt.de", source="https://alt.de/")),
    )
    base.update(over)
    return SiteContent(**base)


def test_valid_content_passes():
    assert validate_content(_content(), SOURCE).ok


def test_schema_rejects_extra_fields_and_long_highlights():
    with pytest.raises(ValidationError):
        SiteContent.model_validate({**_content().model_dump(), "rating": "5 Sterne"})
    with pytest.raises(ValidationError):
        _content(highlights=["x" * 80])


def test_llm_schema_has_no_hero_image():
    schema = json_schema_for_llm()
    assert "hero_image" not in schema["properties"]
    assert schema["additionalProperties"] is False


def test_invented_price_is_flagged():
    r = validate_content(_content(services=[ServiceItem(name=Sourced(value="Klasse B", source="x"), price=Sourced(value="249,00 €", source="x"))]), SOURCE)
    assert not r.ok and "249" in r.warnings[0]


def test_invented_team_member_is_flagged():
    r = validate_content(_content(team=[TeamMember(name=Sourced(value="Max Mustermann", source="x"))]), SOURCE)
    assert any("Max Mustermann" in w for w in r.warnings)


def test_invented_phone_and_time_are_flagged():
    r = validate_content(_content(contact=Contact(phone=Sourced(value="0221 999999", source="x"))), SOURCE)
    assert any("Telefonnummer" in w for w in r.warnings)
    r = validate_content(_content(hours=[HoursBlock(label="Theorie", entries=[Sourced(value="Mo 19:00 – 20:30 Uhr", source="x")])]), SOURCE)
    assert any("Zahl" in w or "Uhrzeit" in w for w in r.warnings)


def test_invented_class_is_flagged():
    r = validate_content(_content(services=[ServiceItem(name=Sourced(value="Klasse CE", source="x"))]), SOURCE)
    assert any("Klasse CE" in w for w in r.warnings)


def test_marketing_claims_are_flagged():
    r = validate_content(_content(about="Seit 1985 die beste Fahrschule mit 98 % Bestehensquote."), SOURCE)
    assert any("1985" in w or "Behauptung" in w for w in r.warnings)
    r = validate_content(_content(about="Wir bilden in Köln aus und nehmen uns Zeit."), SOURCE)
    assert r.ok


def test_obfuscated_email_in_source_is_accepted():
    assert validate_content(_content(), SOURCE).ok  # info@alt.de appears only as "info [at] alt [dot] de"
