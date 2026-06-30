"""
Focused tests for config hardening (Fix 2).

Verifies:
- Production fails fast for missing critical env vars.
- Development/test preserves current defaults.
- APP_ENV defaulting to development issues a warning.
- DB_PROVIDER defaulting to json issues a warning.
- JSON_STORAGE_PATH is required in production with DB_PROVIDER=json.
"""
from __future__ import annotations

import pytest

from nexa_engine.modules.shared.config.app_settings import (
    APP_ENV_DEVELOPMENT,
    APP_ENV_PRODUCTION,
    APP_ENV_TEST,
    load_app_settings,
)
from nexa_engine.db.config import load_config
from nexa_engine.db.exceptions import DbConfigurationError


# ─────────────────────────────────────────────────────────────────────────────
# APP_ENV hardening
# ─────────────────────────────────────────────────────────────────────────────

class TestAppEnvHardening:

    def test_development_default_when_unset(self):
        """When APP_ENV is not set, defaults to development."""
        settings = load_app_settings(env={})
        assert settings.app_env == APP_ENV_DEVELOPMENT

    def test_development_default_emits_warning(self, caplog):
        """When APP_ENV is not set, a WARNING is logged."""
        import logging
        with caplog.at_level(logging.WARNING, logger="nexa"):
            load_app_settings(env={})
        assert any("APP_ENV" in msg for msg in caplog.messages)

    def test_explicit_production_no_warning(self, caplog):
        """When APP_ENV=production is set, no APP_ENV missing warning."""
        import logging
        with caplog.at_level(logging.WARNING, logger="nexa"):
            try:
                load_app_settings(env={
                    "APP_ENV": "production",
                    "CORS_ALLOWED_ORIGINS": "https://app.example.com",
                })
            except DbConfigurationError:
                pass  # JSON_STORAGE_PATH may raise, that's fine
        warning_msgs = [m for m in caplog.messages if "APP_ENV not set" in m]
        assert not warning_msgs

    def test_docs_enabled_in_development(self):
        """Swagger docs are enabled in development mode."""
        settings = load_app_settings(env={"APP_ENV": "development"})
        assert settings.docs_enabled is True

    def test_docs_disabled_in_production(self):
        """Swagger docs are disabled in production mode."""
        settings = load_app_settings(env={
            "APP_ENV": "production",
            "CORS_ALLOWED_ORIGINS": "https://app.example.com",
            "JSON_STORAGE_PATH": "/tmp/nexa_test_storage",
        })
        assert settings.docs_enabled is False

    def test_invalid_app_env_raises(self):
        """Invalid APP_ENV value raises DbConfigurationError."""
        with pytest.raises(DbConfigurationError, match="APP_ENV"):
            load_app_settings(env={"APP_ENV": "staging"})


# ─────────────────────────────────────────────────────────────────────────────
# DB_PROVIDER hardening
# ─────────────────────────────────────────────────────────────────────────────

class TestDbProviderHardening:

    def test_json_default_when_unset(self):
        """When DB_PROVIDER is not set, defaults to json."""
        config = load_config(env={})
        assert config.provider == "json"

    def test_json_default_emits_warning(self, caplog):
        """When DB_PROVIDER is not set, a WARNING is logged."""
        import logging
        with caplog.at_level(logging.WARNING, logger="nexa.db.config"):
            load_config(env={})
        assert any("DB_PROVIDER" in msg for msg in caplog.messages)

    def test_explicit_json_no_warning(self, caplog):
        """When DB_PROVIDER=json is explicitly set, no missing warning."""
        import logging
        with caplog.at_level(logging.WARNING, logger="nexa.db.config"):
            load_config(env={"DB_PROVIDER": "json"})
        warning_msgs = [m for m in caplog.messages if "DB_PROVIDER not set" in m]
        assert not warning_msgs

    def test_invalid_db_provider_raises(self):
        """Invalid DB_PROVIDER value raises DbConfigurationError."""
        with pytest.raises(DbConfigurationError, match="DB_PROVIDER"):
            load_config(env={"DB_PROVIDER": "redis"})


# ─────────────────────────────────────────────────────────────────────────────
# JSON_STORAGE_PATH hardening (production)
# ─────────────────────────────────────────────────────────────────────────────

class TestJsonStoragePathHardening:

    def test_production_json_without_path_raises(self):
        """APP_ENV=production + DB_PROVIDER=json + no JSON_STORAGE_PATH raises."""
        with pytest.raises(DbConfigurationError, match="JSON_STORAGE_PATH"):
            load_config(env={"APP_ENV": "production", "DB_PROVIDER": "json"})

    def test_production_json_with_explicit_path_ok(self, tmp_path):
        """APP_ENV=production + DB_PROVIDER=json + explicit JSON_STORAGE_PATH is valid."""
        config = load_config(env={
            "APP_ENV": "production",
            "DB_PROVIDER": "json",
            "JSON_STORAGE_PATH": str(tmp_path),
        })
        assert config.provider == "json"
        assert config.json_storage_path == tmp_path

    def test_development_json_without_path_uses_default(self):
        """In development, missing JSON_STORAGE_PATH uses project default (no error)."""
        config = load_config(env={"APP_ENV": "development", "DB_PROVIDER": "json"})
        assert config.provider == "json"
        assert config.json_storage_path.name == "storage"

    def test_test_env_json_without_path_uses_default(self):
        """In test env, missing JSON_STORAGE_PATH uses project default (no error)."""
        config = load_config(env={"APP_ENV": "test", "DB_PROVIDER": "json"})
        assert config.provider == "json"
        assert config.json_storage_path.name == "storage"
