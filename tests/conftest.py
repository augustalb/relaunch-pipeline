import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _isolated_env(tmp_path, monkeypatch):
    """Every test gets its own SQLite DB and never reads a real .env."""
    monkeypatch.setenv("PIPELINE_ENV_FILE", "/dev/null")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("OUTBOX_DIR", str(tmp_path / "outbox"))
    monkeypatch.setenv("REQUIRE_VERIFIED_EMAIL", "false")
    monkeypatch.setenv("AUTO_APPROVE", "true")
    for key in ("GOOGLE_PLACES_API_KEY", "ANTHROPIC_API_KEY", "INSTANTLY_API_KEY", "CLOUDFLARE_API_TOKEN", "MILLIONVERIFIER_API_KEY", "RESEND_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    from pipeline.config import reset_settings_cache
    from pipeline.db import reset_engine

    reset_settings_cache()
    reset_engine()
    yield
    reset_engine()
    reset_settings_cache()


@pytest.fixture
def fixtures_dir() -> Path:
    return ROOT / "fixtures"
