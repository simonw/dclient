from click.testing import CliRunner
from dclient.cli import cli
import pathlib
import json
import pytest


def test_auth(mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    runner = CliRunner()
    result = runner.invoke(cli, ["auth", "list"])
    assert result.exit_code == 0
    assert result.output.startswith("Tokens file:")
    # Should only have one line
    assert len([line for line in result.output.split("\n") if line.strip()]) == 1

    # Now add a token (keys are now alias names or URLs)
    result2 = runner.invoke(cli, ["auth", "add", "prod"], input="xyz\n")
    assert result2.exit_code == 0

    # Check the tokens file
    auth_file = pathlib.Path(tmpdir) / "auth.json"
    assert json.loads(auth_file.read_text()) == {"prod": "xyz"}

    # auth list should show that now
    result3 = runner.invoke(cli, ["auth", "list"])
    assert result3.output.startswith("Tokens file:")
    assert "prod" in result3.output

    # Remove should fail with an incorrect key
    result4 = runner.invoke(cli, ["auth", "remove", "nonexistent"])
    assert result4.exit_code == 1
    assert result4.output == "Error: No such URL or alias\n"

    # Remove should work with the correct key
    result5 = runner.invoke(cli, ["auth", "remove", "prod"])
    assert result5.exit_code == 0
    assert result5.output == ""

    # Check the tokens file
    auth_file = pathlib.Path(tmpdir) / "auth.json"
    assert json.loads(auth_file.read_text()) == {}


# -- login command (OAuth device flow) --

DEVICE_RESPONSE = {
    "device_code": "devcode123",
    "user_code": "ABCD-EFGH",
    "verification_uri": "https://example.com/-/oauth/device/verify",
    "expires_in": 900,
    "interval": 0,
}

TOKEN_SUCCESS = {
    "access_token": "dstok_abc123",
    "token_type": "bearer",
    "expires_in": 3600,
}


def test_login_with_url(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json=TOKEN_SUCCESS, status_code=200)
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "https://example.com/"])
    assert result.exit_code == 0
    assert "ABCD-EFGH" in result.output
    assert "Login successful" in result.output
    # Token should be saved
    auth_file = pathlib.Path(tmpdir) / "auth.json"
    auths = json.loads(auth_file.read_text())
    assert auths["https://example.com/"] == "dstok_abc123"


def test_login_adds_trailing_slash(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json=TOKEN_SUCCESS, status_code=200)
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "https://example.com"])
    assert result.exit_code == 0
    # Check that the device request went to the right URL
    requests = httpx_mock.get_requests()
    assert str(requests[0].url) == "https://example.com/-/oauth/device"


def test_login_with_alias(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    # Set up an alias first
    config_file = pathlib.Path(tmpdir) / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "default_instance": None,
                "instances": {
                    "prod": {
                        "url": "https://prod.example.com",
                        "default_database": None,
                    }
                },
            }
        )
    )
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json=TOKEN_SUCCESS, status_code=200)
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "prod"])
    assert result.exit_code == 0
    assert "Login successful" in result.output
    # Token should be saved by alias name
    auth_file = pathlib.Path(tmpdir) / "auth.json"
    auths = json.loads(auth_file.read_text())
    assert auths["prod"] == "dstok_abc123"


def test_login_interactive_prompt(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json=TOKEN_SUCCESS, status_code=200)
    runner = CliRunner()
    result = runner.invoke(cli, ["login"], input="https://example.com/\n")
    assert result.exit_code == 0
    assert "Instance URL or alias" in result.output
    assert "Login successful" in result.output


def test_login_access_denied(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json={"error": "access_denied"}, status_code=400)
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "https://example.com/"])
    assert result.exit_code == 1
    assert "Authorization denied" in result.output


def test_login_expired_token(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json={"error": "expired_token"}, status_code=400)
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "https://example.com/"])
    assert result.exit_code == 1
    assert "expired" in result.output


def test_login_pending_then_success(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    # First poll: pending
    httpx_mock.add_response(json={"error": "authorization_pending"}, status_code=400)
    # Second poll: success
    httpx_mock.add_response(json=TOKEN_SUCCESS, status_code=200)
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "https://example.com/"])
    assert result.exit_code == 0
    assert "Login successful" in result.output
    auth_file = pathlib.Path(tmpdir) / "auth.json"
    auths = json.loads(auth_file.read_text())
    assert auths["https://example.com/"] == "dstok_abc123"


def test_login_device_endpoint_error(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(status_code=403)
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "https://example.com/"])
    assert result.exit_code == 1
    assert "Failed to start login flow" in result.output
