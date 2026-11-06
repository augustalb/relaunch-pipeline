from pipeline.schema import json_schema_for_llm

UNSUPPORTED = {"minLength", "maxLength", "pattern", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
               "multipleOf", "minItems", "maxItems", "uniqueItems", "default"}


def _walk(node, path="$"):
    if isinstance(node, dict):
        if node.get("type") == "object":
            assert node.get("additionalProperties") is False, path
        for k, v in node.items():
            assert k not in UNSUPPORTED, f"{path}.{k}"
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}[{i}]")
    yield path


def test_llm_schema_only_uses_supported_keywords():
    schema = json_schema_for_llm()
    list(_walk(schema))
    assert "hero_image" not in schema["properties"]
    assert "hero_image" not in schema.get("required", [])



def test_llm_schema_has_no_optional_or_nullable_fields():
    def walk(node, path="$"):
        if isinstance(node, dict):
            assert "anyOf" not in node, path
            if node.get("type") == "object" and "properties" in node:
                assert set(node["required"]) == set(node["properties"]), path
            for k, v in node.items():
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(json_schema_for_llm())


def test_llm_placeholders_become_none_and_validate():
    from pipeline.schema import SiteContent, normalize_llm_output

    src = "https://fs.de/"
    raw = {
        "industry": "fahrschulen",
        "company_name": {"value": "Fahrschule Muster", "source": src, "snippet": ""},
        "city": "",
        "tagline": "Ihre Fahrschule in Frechen",
        "hero_text": "Klasse B und A.",
        "cta_primary": "Jetzt Kontakt aufnehmen",
        "highlights": [],
        "about": "",
        "services": [{"name": {"value": "Klasse B", "source": src, "snippet": "Klasse B"}, "description": "", "price": {"value": "", "source": "", "snippet": ""}}],
        "prices": [],
        "price_note": "",
        "hours": [{"label": "Bürozeiten", "entries": [{"value": "Mo 15–18 Uhr", "source": src, "snippet": ""}, {"value": "", "source": "", "snippet": ""}]}],
        "team": [{"name": {"value": "Jan Muster", "source": src, "snippet": ""}, "role": ""}],
        "contact": {"phone": {"value": "02234 1234", "source": src, "snippet": ""}, "email": {"value": "", "source": "", "snippet": ""},
                    "address": {"value": "", "source": "", "snippet": ""}, "whatsapp": {"value": "", "source": "", "snippet": ""}},
        "images": [],
    }
    c = SiteContent.model_validate(normalize_llm_output(raw))
    assert c.city is None and c.about is None and c.price_note is None
    assert c.services[0].price is None and c.services[0].description is None
    assert len(c.hours[0].entries) == 1
    assert c.contact.email is None and c.contact.phone.value == "02234 1234"
    assert c.team[0].role is None and c.company_name.snippet is None
