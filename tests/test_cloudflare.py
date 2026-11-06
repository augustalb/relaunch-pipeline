import httpx

from pipeline.config import reset_settings_cache
from pipeline.services import cloudflare


def _setup(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "tok")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acc")
    reset_settings_cache()


def test_ensure_project_creates_missing(monkeypatch):
    _setup(monkeypatch)
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        if request.method == "GET":
            return httpx.Response(404, json={"success": False})
        assert request.headers["Authorization"] == "Bearer tok"
        return httpx.Response(200, json={"success": True, "result": {"name": "relaunch-previews"}})

    assert cloudflare.ensure_project("relaunch-previews", httpx.Client(transport=httpx.MockTransport(handler)))
    assert calls == [("GET", "/client/v4/accounts/acc/pages/projects/relaunch-previews"), ("POST", "/client/v4/accounts/acc/pages/projects")]


def test_ensure_project_existing(monkeypatch):
    _setup(monkeypatch)

    def handler(request):
        assert request.method == "GET"
        return httpx.Response(200, json={"success": True})

    assert cloudflare.ensure_project("relaunch-previews", httpx.Client(transport=httpx.MockTransport(handler)))


def test_ensure_project_without_credentials():
    assert cloudflare.ensure_project("x") is False
