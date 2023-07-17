from click.testing import CliRunner
from dclient.cli import cli
import pathlib
import json


def test_auth(mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    runner = CliRunner()
    result = runner.invoke(cli, ["auth", "list"])
    assert result.exit_code == 0
    assert result.output.startswith("Tokens file:")
    # Should only have one line
    assert len([line for line in result.output.split("\n") if line.strip()]) == 1

    # Now add a token
    result2 = runner.invoke(cli, ["auth", "add", "https://example.com"], input="xyz\n")
    assert result2.exit_code == 0

    # Check the tokens file
    auth_file = pathlib.Path(tmpdir) / "auth.json"
    assert json.loads(auth_file.read_text()) == {"https://example.com": "xyz"}

    # auth list should show that now
    result3 = runner.invoke(cli, ["auth", "list"])
    assert result3.output.startswith("Tokens file:")
    assert "https://example.com" in result3.output

    # Remove should fail with an incorrect URL
    result4 = runner.invoke(cli, ["auth", "remove", "https://example.com/foo"])
    assert result4.exit_code == 1
    assert result4.output == "Error: No such URL or alias\n"

    # Remove should work with the correct URL
    result5 = runner.invoke(cli, ["auth", "remove", "https://example.com"])
    assert result5.exit_code == 0
    assert result5.output == ""

    # Check the tokens file
    auth_file = pathlib.Path(tmpdir) / "auth.json"
    assert json.loads(auth_file.read_text()) == {}
