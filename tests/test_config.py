"""Tests for the v2 config system: config.json format, instance resolution, database resolution."""

from dclient.cli import (
    _load_config,
    _save_config,
    _resolve_instance,
    _resolve_database,
    _resolve_token,
    get_config_dir,
)
import json
import pathlib
import pytest

# -- Config loading/saving --


def test_load_config_empty(tmpdir):
    """Loading config when no file exists returns empty defaults."""
    config_file = pathlib.Path(tmpdir) / "config.json"
    config = _load_config(config_file)
    assert config == {"default_instance": None, "instances": {}}


def test_load_config_existing(tmpdir):
    """Loading config reads the JSON file."""
    config_file = pathlib.Path(tmpdir) / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "default_instance": "prod",
                "instances": {
                    "prod": {
                        "url": "https://myapp.datasette.cloud",
                        "default_database": "main",
                    }
                },
            }
        )
    )
    config = _load_config(config_file)
    assert config["default_instance"] == "prod"
    assert config["instances"]["prod"]["url"] == "https://myapp.datasette.cloud"
    assert config["instances"]["prod"]["default_database"] == "main"


def test_save_config(tmpdir):
    """Saving config writes JSON to disk."""
    config_file = pathlib.Path(tmpdir) / "config.json"
    config = {
        "default_instance": "local",
        "instances": {
            "local": {
                "url": "http://localhost:8001",
                "default_database": None,
            }
        },
    }
    _save_config(config_file, config)
    assert json.loads(config_file.read_text()) == config


# -- Instance resolution --


def test_resolve_instance_from_flag(tmpdir):
    """An explicit -i flag with a URL is used directly."""
    config_file = pathlib.Path(tmpdir) / "config.json"
    url = _resolve_instance("https://example.com", config_file)
    assert url == "https://example.com"


def test_resolve_instance_from_flag_alias(tmpdir):
    """An explicit -i flag with an alias name resolves via config."""
    config_file = pathlib.Path(tmpdir) / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "default_instance": None,
                "instances": {
                    "prod": {
                        "url": "https://myapp.datasette.cloud",
                        "default_database": None,
                    }
                },
            }
        )
    )
    url = _resolve_instance("prod", config_file)
    assert url == "https://myapp.datasette.cloud"


def test_resolve_instance_from_config_default(tmpdir):
    """When no -i flag, uses config.default_instance."""
    config_file = pathlib.Path(tmpdir) / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "default_instance": "prod",
                "instances": {
                    "prod": {
                        "url": "https://myapp.datasette.cloud",
                        "default_database": None,
                    }
                },
            }
        )
    )
    url = _resolve_instance(None, config_file)
    assert url == "https://myapp.datasette.cloud"


def test_resolve_instance_from_env(tmpdir, monkeypatch):
    """When no -i flag and no config default, falls back to DATASETTE_URL."""
    config_file = pathlib.Path(tmpdir) / "config.json"
    monkeypatch.setenv("DATASETTE_URL", "https://env.example.com")
    url = _resolve_instance(None, config_file)
    assert url == "https://env.example.com"


def test_resolve_instance_from_env_strips_trailing_slash(tmpdir, monkeypatch):
    """DATASETTE_URL trailing slash is stripped."""
    config_file = pathlib.Path(tmpdir) / "config.json"
    monkeypatch.setenv("DATASETTE_URL", "https://env.example.com/")
    url = _resolve_instance(None, config_file)
    assert url == "https://env.example.com"


def test_resolve_instance_error(tmpdir, monkeypatch):
    """When nothing is configured, raises an error."""
    config_file = pathlib.Path(tmpdir) / "config.json"
    monkeypatch.delenv("DATASETTE_URL", raising=False)
    with pytest.raises(Exception, match="No instance specified"):
        _resolve_instance(None, config_file)


def test_resolve_instance_unknown_alias(tmpdir):
    """An -i flag with an unknown alias name raises an error."""
    config_file = pathlib.Path(tmpdir) / "config.json"
    config_file.write_text(json.dumps({"default_instance": None, "instances": {}}))
    with pytest.raises(Exception, match="Unknown instance"):
        _resolve_instance("nonexistent", config_file)


# -- Database resolution (optional -d flag mode) --


def test_resolve_database_from_flag(tmpdir):
    """An explicit -d flag is used directly."""
    config_file = pathlib.Path(tmpdir) / "config.json"
    db = _resolve_database("mydb", None, config_file)
    assert db == "mydb"


def test_resolve_database_from_instance_default(tmpdir):
    """When no -d flag, uses the instance's default_database from config."""
    config_file = pathlib.Path(tmpdir) / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "default_instance": "prod",
                "instances": {
                    "prod": {
                        "url": "https://myapp.datasette.cloud",
                        "default_database": "main",
                    }
                },
            }
        )
    )
    db = _resolve_database(None, "prod", config_file)
    assert db == "main"


def test_resolve_database_from_env(tmpdir, monkeypatch):
    """When no -d flag and no instance default, falls back to DATASETTE_DATABASE."""
    config_file = pathlib.Path(tmpdir) / "config.json"
    monkeypatch.setenv("DATASETTE_DATABASE", "envdb")
    db = _resolve_database(None, None, config_file)
    assert db == "envdb"


def test_resolve_database_error(tmpdir, monkeypatch):
    """When nothing is configured, raises an error."""
    config_file = pathlib.Path(tmpdir) / "config.json"
    monkeypatch.delenv("DATASETTE_DATABASE", raising=False)
    with pytest.raises(Exception, match="No database specified"):
        _resolve_database(None, None, config_file)


# -- Token resolution --


def test_resolve_token_from_flag(tmpdir):
    """An explicit --token flag is used directly."""
    auth_file = pathlib.Path(tmpdir) / "auth.json"
    config_file = pathlib.Path(tmpdir) / "config.json"
    token = _resolve_token(
        "explicit-token", "https://example.com", auth_file, config_file
    )
    assert token == "explicit-token"


def test_resolve_token_from_auth_by_alias(tmpdir):
    """Auth token looked up by alias name."""
    auth_file = pathlib.Path(tmpdir) / "auth.json"
    auth_file.write_text(json.dumps({"prod": "tok123"}))
    config_file = pathlib.Path(tmpdir) / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "default_instance": None,
                "instances": {
                    "prod": {
                        "url": "https://myapp.datasette.cloud",
                        "default_database": None,
                    }
                },
            }
        )
    )
    token = _resolve_token(
        None, "https://myapp.datasette.cloud", auth_file, config_file
    )
    assert token == "tok123"


def test_resolve_token_from_auth_by_url_fallback(tmpdir):
    """Auth token falls back to URL prefix matching when no alias match."""
    auth_file = pathlib.Path(tmpdir) / "auth.json"
    auth_file.write_text(json.dumps({"https://example.com": "url-tok"}))
    config_file = pathlib.Path(tmpdir) / "config.json"
    token = _resolve_token(None, "https://example.com/db", auth_file, config_file)
    assert token == "url-tok"


def test_resolve_token_from_env(tmpdir, monkeypatch):
    """Falls back to DATASETTE_TOKEN env var."""
    auth_file = pathlib.Path(tmpdir) / "auth.json"
    config_file = pathlib.Path(tmpdir) / "config.json"
    monkeypatch.setenv("DATASETTE_TOKEN", "env-tok")
    token = _resolve_token(None, "https://example.com", auth_file, config_file)
    assert token == "env-tok"


def test_resolve_token_none(tmpdir, monkeypatch):
    """Returns None when nothing is configured."""
    auth_file = pathlib.Path(tmpdir) / "auth.json"
    config_file = pathlib.Path(tmpdir) / "config.json"
    monkeypatch.delenv("DATASETTE_TOKEN", raising=False)
    token = _resolve_token(None, "https://example.com", auth_file, config_file)
    assert token is None
