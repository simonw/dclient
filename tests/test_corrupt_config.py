"""A corrupt config.json should be a clean CLI error, not a traceback."""

from click.testing import CliRunner
from dclient.cli import cli
import json
import pathlib


def test_alias_list_corrupt_config(mocker, tmpdir):
    config_dir = pathlib.Path(tmpdir)
    (config_dir / "config.json").write_text("{not valid json")
    mocker.patch("dclient.cli.get_config_dir", return_value=config_dir)
    result = CliRunner().invoke(cli, ["alias", "list"])
    assert result.exit_code == 1
    assert not isinstance(result.exception, json.JSONDecodeError)
    assert "config.json" in result.output
