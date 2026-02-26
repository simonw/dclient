"""Tests for v1 → v2 config migration."""

from dclient.cli import _migrate_v1_to_v2
import json
import pathlib


def test_migration_simple(tmpdir):
    """Migrate a simple aliases.json with a database-in-URL alias."""
    config_dir = pathlib.Path(tmpdir)
    aliases_file = config_dir / "aliases.json"
    aliases_file.write_text(
        json.dumps({"content": "https://datasette.io/content"})
    )

    _migrate_v1_to_v2(config_dir)

    config = json.loads((config_dir / "config.json").read_text())
    assert config["instances"]["content"]["url"] == "https://datasette.io"
    assert config["instances"]["content"]["default_database"] == "content"
    assert config["default_instance"] is None

    # Original should be renamed
    assert (config_dir / "aliases.json.bak").exists()
    assert not (config_dir / "aliases.json").exists()


def test_migration_no_path_segment(tmpdir):
    """Migrate an alias that has no database in the URL."""
    config_dir = pathlib.Path(tmpdir)
    aliases_file = config_dir / "aliases.json"
    aliases_file.write_text(
        json.dumps({"local": "http://localhost:8001"})
    )

    _migrate_v1_to_v2(config_dir)

    config = json.loads((config_dir / "config.json").read_text())
    assert config["instances"]["local"]["url"] == "http://localhost:8001"
    assert config["instances"]["local"]["default_database"] is None


def test_migration_with_auth(tmpdir):
    """Auth keys are migrated from URLs to alias names."""
    config_dir = pathlib.Path(tmpdir)
    aliases_file = config_dir / "aliases.json"
    aliases_file.write_text(
        json.dumps({"content": "https://datasette.io/content"})
    )
    auth_file = config_dir / "auth.json"
    auth_file.write_text(
        json.dumps({"https://datasette.io/content": "tok123"})
    )

    _migrate_v1_to_v2(config_dir)

    new_auths = json.loads((config_dir / "auth.json").read_text())
    assert "content" in new_auths
    assert new_auths["content"] == "tok123"

    # Old auth should be backed up
    assert (config_dir / "auth.json.bak").exists()


def test_migration_auth_url_fallback(tmpdir):
    """Auth entries without matching aliases are kept as URL keys."""
    config_dir = pathlib.Path(tmpdir)
    aliases_file = config_dir / "aliases.json"
    aliases_file.write_text(json.dumps({}))
    auth_file = config_dir / "auth.json"
    auth_file.write_text(
        json.dumps({"https://other.example.com": "tok456"})
    )

    _migrate_v1_to_v2(config_dir)

    new_auths = json.loads((config_dir / "auth.json").read_text())
    assert new_auths["https://other.example.com"] == "tok456"


def test_migration_skips_if_config_exists(tmpdir):
    """If config.json already exists, migration is skipped."""
    config_dir = pathlib.Path(tmpdir)
    (config_dir / "config.json").write_text(json.dumps({"existing": True}))
    (config_dir / "aliases.json").write_text(json.dumps({"foo": "https://bar.com"}))

    _migrate_v1_to_v2(config_dir)

    # config.json should be untouched
    assert json.loads((config_dir / "config.json").read_text()) == {"existing": True}
    # aliases.json should NOT be renamed
    assert (config_dir / "aliases.json").exists()


def test_migration_skips_if_no_aliases(tmpdir):
    """If aliases.json doesn't exist, migration is skipped."""
    config_dir = pathlib.Path(tmpdir)

    _migrate_v1_to_v2(config_dir)

    assert not (config_dir / "config.json").exists()


def test_migration_multi_path_segments(tmpdir):
    """URL with multiple path segments stores URL as-is."""
    config_dir = pathlib.Path(tmpdir)
    aliases_file = config_dir / "aliases.json"
    aliases_file.write_text(
        json.dumps({"deep": "https://example.com/a/b/c"})
    )

    _migrate_v1_to_v2(config_dir)

    config = json.loads((config_dir / "config.json").read_text())
    assert config["instances"]["deep"]["url"] == "https://example.com/a/b/c"
    assert config["instances"]["deep"]["default_database"] is None
