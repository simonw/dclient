"""Tests for v2 alias command: default, default-db subcommands."""

from click.testing import CliRunner
from dclient.cli import cli
import json
import pathlib


def test_alias_default_workflow(mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    runner = CliRunner()

    # Add an alias
    result = runner.invoke(cli, ["alias", "add", "prod", "https://prod.example.com"])
    assert result.exit_code == 0

    # No default yet
    result = runner.invoke(cli, ["alias", "default"])
    assert result.exit_code == 0
    assert "No default instance set" in result.output

    # Set default
    result = runner.invoke(cli, ["alias", "default", "prod"])
    assert result.exit_code == 0

    # Show default
    result = runner.invoke(cli, ["alias", "default"])
    assert result.exit_code == 0
    assert result.output.strip() == "prod"

    # List should show * marker
    result = runner.invoke(cli, ["alias", "list"])
    assert result.exit_code == 0
    assert "* prod" in result.output

    # Clear default
    result = runner.invoke(cli, ["alias", "default", "--clear"])
    assert result.exit_code == 0

    result = runner.invoke(cli, ["alias", "default"])
    assert "No default instance set" in result.output


def test_alias_default_unknown_alias(mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    runner = CliRunner()
    result = runner.invoke(cli, ["alias", "default", "nonexistent"])
    assert result.exit_code == 1
    assert "No such alias" in result.output


def test_alias_default_db_workflow(mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    runner = CliRunner()

    # Add an alias
    result = runner.invoke(cli, ["alias", "add", "prod", "https://prod.example.com"])
    assert result.exit_code == 0

    # No default database yet
    result = runner.invoke(cli, ["alias", "default-db", "prod"])
    assert result.exit_code == 0
    assert "No default database set" in result.output

    # Set default database
    result = runner.invoke(cli, ["alias", "default-db", "prod", "main"])
    assert result.exit_code == 0

    # Show default database
    result = runner.invoke(cli, ["alias", "default-db", "prod"])
    assert result.exit_code == 0
    assert result.output.strip() == "main"

    # List should show db info
    result = runner.invoke(cli, ["alias", "list"])
    assert "(db: main)" in result.output

    # Clear default database
    result = runner.invoke(cli, ["alias", "default-db", "prod", "--clear"])
    assert result.exit_code == 0

    result = runner.invoke(cli, ["alias", "default-db", "prod"])
    assert "No default database set" in result.output


def test_alias_default_db_unknown_alias(mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    runner = CliRunner()
    result = runner.invoke(cli, ["alias", "default-db", "nonexistent", "main"])
    assert result.exit_code == 1
    assert "No such alias" in result.output


def test_alias_remove_clears_default(mocker, tmpdir):
    """Removing the default alias also clears default_instance."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    runner = CliRunner()

    runner.invoke(cli, ["alias", "add", "prod", "https://prod.example.com"])
    runner.invoke(cli, ["alias", "default", "prod"])

    # Verify it's set
    config = json.loads((pathlib.Path(tmpdir) / "config.json").read_text())
    assert config["default_instance"] == "prod"

    # Remove alias
    runner.invoke(cli, ["alias", "remove", "prod"])

    config = json.loads((pathlib.Path(tmpdir) / "config.json").read_text())
    assert config["default_instance"] is None
    assert "prod" not in config["instances"]
