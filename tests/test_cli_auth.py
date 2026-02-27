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
    httpx_mock.add_response(json=[{"name": "data"}], status_code=200)
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
    httpx_mock.add_response(json=[{"name": "data"}], status_code=200)
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
    httpx_mock.add_response(json=[{"name": "data"}], status_code=200)
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
    httpx_mock.add_response(json=[{"name": "data"}], status_code=200)
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
    httpx_mock.add_response(json=[{"name": "data"}], status_code=200)
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


# -- login sets defaults --


@pytest.mark.parametrize(
    "databases_response,expected_db",
    [
        ([{"name": "mydata", "is_mutable": True}], "mydata"),
        (
            [
                {"name": "fixtures", "is_mutable": False},
                {"name": "data", "is_mutable": True},
                {"name": "extra", "is_mutable": True},
            ],
            "data",
        ),
        (
            [
                {"name": "alpha", "is_mutable": True},
                {"name": "beta", "is_mutable": True},
                {"name": "gamma", "is_mutable": False},
            ],
            "alpha",
        ),
    ],
    ids=["single_db", "prefers_data", "first_when_no_data"],
)
def test_login_sets_defaults(
    httpx_mock, mocker, tmpdir, databases_response, expected_db
):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json=TOKEN_SUCCESS, status_code=200)
    httpx_mock.add_response(json=databases_response, status_code=200)
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "https://example.com/"])
    assert result.exit_code == 0, result.output
    config = json.loads((pathlib.Path(tmpdir) / "config.json").read_text())
    assert config["default_instance"] == "https://example.com/"
    assert (
        config["instances"]["https://example.com/"]["default_database"] == expected_db
    )


def test_login_does_not_override_existing_defaults(httpx_mock, mocker, tmpdir):
    """When defaults are already configured, login should not change them."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    config_file = pathlib.Path(tmpdir) / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "default_instance": "prod",
                "instances": {
                    "prod": {
                        "url": "https://prod.example.com",
                        "default_database": "main",
                    }
                },
            }
        )
    )
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json=TOKEN_SUCCESS, status_code=200)
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "https://other.example.com/"])
    assert result.exit_code == 0, result.output
    config = json.loads(config_file.read_text())
    assert config["default_instance"] == "prod"


def test_login_with_alias_sets_defaults(httpx_mock, mocker, tmpdir):
    """When logging in with an alias that has no default_database, set it."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
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
    httpx_mock.add_response(
        json=[
            {"name": "fixtures", "is_mutable": False},
            {"name": "data", "is_mutable": True},
            {"name": "extra", "is_mutable": True},
        ],
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "prod"])
    assert result.exit_code == 0, result.output
    config = json.loads(config_file.read_text())
    assert config["default_instance"] == "prod"
    assert config["instances"]["prod"]["default_database"] == "data"


def test_login_read_all(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json=TOKEN_SUCCESS, status_code=200)
    httpx_mock.add_response(json=[{"name": "data"}], status_code=200)
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "https://example.com/", "--read-all"])
    assert result.exit_code == 0, result.output
    from urllib.parse import parse_qs

    request = httpx_mock.get_requests()[0]
    body = parse_qs(request.content.decode())
    scope = json.loads(body["scope"][0])
    assert scope == [
        ["view-instance"],
        ["view-table"],
        ["view-database"],
        ["view-query"],
        ["execute-sql"],
    ]


def test_login_write_all(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json=TOKEN_SUCCESS, status_code=200)
    httpx_mock.add_response(json=[{"name": "data"}], status_code=200)
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "https://example.com/", "--write-all"])
    assert result.exit_code == 0, result.output
    from urllib.parse import parse_qs

    request = httpx_mock.get_requests()[0]
    body = parse_qs(request.content.decode())
    scope = json.loads(body["scope"][0])
    assert scope == [
        ["view-instance"],
        ["view-table"],
        ["view-database"],
        ["view-query"],
        ["execute-sql"],
        ["insert-row"],
        ["delete-row"],
        ["update-row"],
        ["create-table"],
        ["alter-table"],
        ["drop-table"],
    ]


def test_login_read_database(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json=TOKEN_SUCCESS, status_code=200)
    httpx_mock.add_response(json=[{"name": "data"}], status_code=200)
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "https://example.com/", "--read", "db1"])
    assert result.exit_code == 0, result.output
    from urllib.parse import parse_qs

    request = httpx_mock.get_requests()[0]
    body = parse_qs(request.content.decode())
    scope = json.loads(body["scope"][0])
    assert scope == [
        ["view-instance", "db1"],
        ["view-table", "db1"],
        ["view-database", "db1"],
        ["view-query", "db1"],
        ["execute-sql", "db1"],
    ]


def test_login_write_table(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json=TOKEN_SUCCESS, status_code=200)
    httpx_mock.add_response(json=[{"name": "data"}], status_code=200)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["login", "https://example.com/", "--write", "db3/submissions"]
    )
    assert result.exit_code == 0, result.output
    from urllib.parse import parse_qs

    request = httpx_mock.get_requests()[0]
    body = parse_qs(request.content.decode())
    scope = json.loads(body["scope"][0])
    assert scope == [
        ["view-instance", "db3", "submissions"],
        ["view-table", "db3", "submissions"],
        ["view-database", "db3", "submissions"],
        ["view-query", "db3", "submissions"],
        ["execute-sql", "db3", "submissions"],
        ["insert-row", "db3", "submissions"],
        ["delete-row", "db3", "submissions"],
        ["update-row", "db3", "submissions"],
        ["create-table", "db3", "submissions"],
        ["alter-table", "db3", "submissions"],
        ["drop-table", "db3", "submissions"],
    ]


def test_login_mixed_read_write(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json=TOKEN_SUCCESS, status_code=200)
    httpx_mock.add_response(json=[{"name": "data"}], status_code=200)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["login", "https://example.com/", "--read", "db1", "--write", "db3/dogs"],
    )
    assert result.exit_code == 0, result.output
    from urllib.parse import parse_qs

    request = httpx_mock.get_requests()[0]
    body = parse_qs(request.content.decode())
    scope = json.loads(body["scope"][0])
    assert scope == [
        ["view-instance", "db1"],
        ["view-table", "db1"],
        ["view-database", "db1"],
        ["view-query", "db1"],
        ["execute-sql", "db1"],
        ["view-instance", "db3", "dogs"],
        ["view-table", "db3", "dogs"],
        ["view-database", "db3", "dogs"],
        ["view-query", "db3", "dogs"],
        ["execute-sql", "db3", "dogs"],
        ["insert-row", "db3", "dogs"],
        ["delete-row", "db3", "dogs"],
        ["update-row", "db3", "dogs"],
        ["create-table", "db3", "dogs"],
        ["alter-table", "db3", "dogs"],
        ["drop-table", "db3", "dogs"],
    ]


def test_login_scope_combined_with_shortcuts(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json=TOKEN_SUCCESS, status_code=200)
    httpx_mock.add_response(json=[{"name": "data"}], status_code=200)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "login",
            "https://example.com/",
            "--scope",
            '[["view-instance"]]',
            "--write",
            "db1/dogs",
        ],
    )
    assert result.exit_code == 0, result.output
    from urllib.parse import parse_qs

    request = httpx_mock.get_requests()[0]
    body = parse_qs(request.content.decode())
    scope = json.loads(body["scope"][0])
    assert scope == [
        ["view-instance"],
        ["view-instance", "db1", "dogs"],
        ["view-table", "db1", "dogs"],
        ["view-database", "db1", "dogs"],
        ["view-query", "db1", "dogs"],
        ["execute-sql", "db1", "dogs"],
        ["insert-row", "db1", "dogs"],
        ["delete-row", "db1", "dogs"],
        ["update-row", "db1", "dogs"],
        ["create-table", "db1", "dogs"],
        ["alter-table", "db1", "dogs"],
        ["drop-table", "db1", "dogs"],
    ]


def test_login_no_scope_sends_no_scope(httpx_mock, mocker, tmpdir):
    """Without any scope options, no scope field should be sent."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json=TOKEN_SUCCESS, status_code=200)
    httpx_mock.add_response(json=[{"name": "data"}], status_code=200)
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "https://example.com/"])
    assert result.exit_code == 0, result.output
    request = httpx_mock.get_requests()[0]
    assert request.content == b""


def test_login_token_only(httpx_mock, mocker, tmpdir):
    """--token-only prints the token to stdout and does not save it."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json=TOKEN_SUCCESS, status_code=200)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["login", "https://example.com/", "--token-only", "--read", "foo/bar"]
    )
    assert result.exit_code == 0, result.output
    # Last line of output should be the raw token
    assert result.output.strip().endswith("dstok_abc123")
    # Should NOT have "Login successful" message
    assert "Login successful" not in result.output
    # auth.json should not exist
    auth_file = pathlib.Path(tmpdir) / "auth.json"
    assert not auth_file.exists()
    # config.json should not exist (no defaults set)
    config_file = pathlib.Path(tmpdir) / "config.json"
    assert not config_file.exists()


def test_login_databases_error_still_succeeds(httpx_mock, mocker, tmpdir):
    """If the databases check fails, login should still succeed."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    mocker.patch("dclient.cli.time.sleep")
    httpx_mock.add_response(json=DEVICE_RESPONSE, status_code=200)
    httpx_mock.add_response(json=TOKEN_SUCCESS, status_code=200)
    httpx_mock.add_response(status_code=500)
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "https://example.com/"])
    assert result.exit_code == 0, result.output
    assert "Login successful" in result.output
