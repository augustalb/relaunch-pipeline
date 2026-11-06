import httpx

from pipeline import livecheck
from pipeline.config import reset_settings_cache


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_missing_keys_are_reported_not_failed(monkeypatch):
    for k in ["GOOGLE_PLACES_API_KEY", "PAGESPEED_API_KEY", "ANTHROPIC_API_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"]:
        monkeypatch.setenv(k, "")
    reset_settings_cache()

    def handler(request):  # pragma: no cover - must not be called
        raise AssertionError(f"unexpected request {request.url}")

    results = livecheck.run_live_checks(_client(handler))
    by = {r.name: r for r in results}
    assert by["Datenbank"].status == "ok"
    for name in ["Google Places", "PageSpeed", "Anthropic", "Cloudflare"]:
        assert by[name].status == "nicht gesetzt"
    assert not any(r.failed for r in results)


def test_ok_and_error_responses(monkeypatch):
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "k1")
    monkeypatch.setenv("PAGESPEED_API_KEY", "k2")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k3")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "k4")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acc")
    reset_settings_cache()

    def handler(request):
        host = request.url.host
        if host == "places.googleapis.com":
            assert request.headers["X-Goog-FieldMask"] == "places.id"
            return httpx.Response(200, json={"places": [{"id": "x"}]})
        if host == "www.googleapis.com":
            return httpx.Response(200, json={"lighthouseResult": {"categories": {"performance": {"score": 0.97}}}})
        if host == "api.anthropic.com":
            return httpx.Response(401, json={"error": {"message": "invalid x-api-key"}})  # stops before the schema check
        if host == "api.cloudflare.com":
            return httpx.Response(200, json={"success": True, "result": [{"name": "relaunch-previews"}]})
        raise AssertionError(host)

    by = {r.name: r for r in livecheck.run_live_checks(_client(handler))}
    assert by["Google Places"].status == "ok"
    assert by["PageSpeed"].status == "ok" and "97" in by["PageSpeed"].detail
    assert by["Anthropic"].failed and "401" in by["Anthropic"].detail
    assert by["Cloudflare"].status == "ok" and "vorhanden" in by["Cloudflare"].detail
    for r in by.values():
        assert "k1" not in r.detail and "k3" not in r.detail and "k4" not in r.detail


def test_anthropic_schema_check(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k3")
    reset_settings_cache()
    seen = []

    def handler(request):
        seen.append(request.url.path)
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "claude-haiku-5-5"}]})
        body = __import__("json").loads(request.content)
        assert body["output_config"]["format"]["type"] == "json_schema"
        return httpx.Response(400, json={"error": {"message": "maxLength not supported"}})

    r = livecheck.check_anthropic(_client(handler))
    assert seen == ["/v1/models", "/v1/messages"]
    assert r.failed and "Schema abgelehnt" in r.detail


def test_anthropic_schema_timeout_is_not_a_failure(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k3")
    reset_settings_cache()

    def handler(request):
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "claude-haiku-5-5"}]})
        raise httpx.ReadTimeout("slow", request=request)

    r = livecheck.check_anthropic(_client(handler))
    assert not r.failed and "Zeitüberschreitung" in r.detail
