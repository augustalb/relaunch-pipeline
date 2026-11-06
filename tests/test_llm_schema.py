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
