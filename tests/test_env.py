from click.testing import CliRunner
from dclient.cli import cli
import json
import pathlib


QUERY_RESPONSE = {
    "ok": True,
    "database": "data",
    "query_name": None,
    "rows": [{"id": 1}],
    "truncated": False,
    "columns": ["id"],
    "query": {"sql": "select 1", "params": {}},
    "error": None,
    "private": False,
    "allow_execute_sql": True,
}


# -- DATASETTE_TOKEN tests --


def test_datasette_token_used_as_fallback(httpx_mock, mocker, tmpdir):
    """DATASETTE_TOKEN is used when no --token flag and no auth.json match."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(json=QUERY_RESPONSE, status_code=200)
    runner = CliRunner(env={"DATASETTE_TOKEN": "env-token-123"})
    result = runner.invoke(cli, ["query", "https://example.com", "select 1"])
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.headers["authorization"] == "Bearer env-token-123"


def test_token_flag_overrides_datasette_token(httpx_mock, mocker, tmpdir):
    """--token flag takes priority over DATASETTE_TOKEN."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(json=QUERY_RESPONSE, status_code=200)
    runner = CliRunner(env={"DATASETTE_TOKEN": "env-token"})
    result = runner.invoke(
        cli, ["query", "https://example.com", "select 1", "--token", "flag-token"]
    )
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.headers["authorization"] == "Bearer flag-token"


def test_auth_json_overrides_datasette_token(httpx_mock, mocker, tmpdir):
    """Stored auth.json token takes priority over DATASETTE_TOKEN."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    auth_file = pathlib.Path(tmpdir) / "auth.json"
    auth_file.write_text(json.dumps({"https://example.com": "stored-token"}))
    httpx_mock.add_response(json=QUERY_RESPONSE, status_code=200)
    runner = CliRunner(env={"DATASETTE_TOKEN": "env-token"})
    result = runner.invoke(cli, ["query", "https://example.com", "select 1"])
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.headers["authorization"] == "Bearer stored-token"


# -- DATASETTE_URL tests --


def test_datasette_url_combines_with_database_name(httpx_mock, mocker, tmpdir):
    """DATASETTE_URL + database name arg → combined URL."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(json=QUERY_RESPONSE, status_code=200)
    runner = CliRunner(env={"DATASETTE_URL": "https://my-instance.datasette.cloud"})
    result = runner.invoke(cli, ["query", "data", "select 1"])
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.url.host == "my-instance.datasette.cloud"
    assert request.url.path == "/data.json"


def test_datasette_url_with_trailing_slash(httpx_mock, mocker, tmpdir):
    """DATASETTE_URL with trailing slash still works correctly."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(json=QUERY_RESPONSE, status_code=200)
    runner = CliRunner(env={"DATASETTE_URL": "https://my-instance.datasette.cloud/"})
    result = runner.invoke(cli, ["query", "data", "select 1"])
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.url.path == "/data.json"


def test_full_url_ignores_datasette_url(httpx_mock, mocker, tmpdir):
    """A full URL argument is used as-is, ignoring DATASETTE_URL."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(json=QUERY_RESPONSE, status_code=200)
    runner = CliRunner(env={"DATASETTE_URL": "https://should-be-ignored.com"})
    result = runner.invoke(cli, ["query", "https://other.example.com/db", "select 1"])
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.url.host == "other.example.com"
    assert request.url.path == "/db.json"


def test_alias_takes_priority_over_datasette_url(httpx_mock, mocker, tmpdir):
    """Alias match takes priority over DATASETTE_URL."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    aliases_file = pathlib.Path(tmpdir) / "aliases.json"
    aliases_file.write_text(json.dumps({"myalias": "https://aliased.example.com/db"}))
    httpx_mock.add_response(json=QUERY_RESPONSE, status_code=200)
    runner = CliRunner(env={"DATASETTE_URL": "https://should-be-ignored.com"})
    result = runner.invoke(cli, ["query", "myalias", "select 1"])
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.url.host == "aliased.example.com"
    assert request.url.path == "/db.json"


# -- DATASETTE_URL with other commands --


def test_datasette_url_with_insert(httpx_mock, mocker, tmpdir):
    """DATASETTE_URL works with the insert command."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(json={"ok": True}, status_code=200)
    csv_path = pathlib.Path(tmpdir) / "data.csv"
    csv_path.write_text("id,name\n1,hello\n")
    runner = CliRunner(
        env={
            "DATASETTE_URL": "https://my-instance.datasette.cloud",
            "DATASETTE_TOKEN": "env-token",
        }
    )
    result = runner.invoke(
        cli,
        ["insert", "data", "my_table", str(csv_path), "--csv", "--create"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.url.host == "my-instance.datasette.cloud"
    assert "/-/create" in str(request.url.path)
    assert request.headers["authorization"] == "Bearer env-token"


def test_datasette_url_with_actor(httpx_mock, mocker, tmpdir):
    """DATASETTE_URL works with the actor command."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={"actor": {"id": "root"}},
        status_code=200,
    )
    runner = CliRunner(
        env={
            "DATASETTE_URL": "https://my-instance.datasette.cloud",
            "DATASETTE_TOKEN": "env-token",
        }
    )
    result = runner.invoke(cli, ["actor", "data"])
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.url.host == "my-instance.datasette.cloud"
    assert request.headers["authorization"] == "Bearer env-token"


# -- Both together --


def test_datasette_url_and_token_together(httpx_mock, mocker, tmpdir):
    """DATASETTE_URL and DATASETTE_TOKEN work together for a complete config."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(json=QUERY_RESPONSE, status_code=200)
    runner = CliRunner(
        env={
            "DATASETTE_URL": "https://my-instance.datasette.cloud",
            "DATASETTE_TOKEN": "env-token-456",
        }
    )
    result = runner.invoke(cli, ["query", "mydb", "select 1"])
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.url.host == "my-instance.datasette.cloud"
    assert request.url.path == "/mydb.json"
    assert request.headers["authorization"] == "Bearer env-token-456"
