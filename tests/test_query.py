from click.testing import CliRunner
from dclient.cli import cli
import json
import pathlib


def test_query_error(httpx_mock):
    httpx_mock.add_response(
        json={
            "ok": False,
            "error": "Statement must be a SELECT",
            "status": 400,
            "title": "Invalid SQL",
        },
        status_code=400,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["query", "https://example.com", "hello"])
    assert result.exit_code == 1
    assert result.output == "Error: Invalid SQL: Statement must be a SELECT\n"


def test_query(httpx_mock):
    httpx_mock.add_response(
        json={
            "ok": True,
            "database": "fixtures",
            "query_name": None,
            "rows": [{"5 * 2": 10}],
            "truncated": False,
            "columns": ["5 * 2"],
            "query": {"sql": "select 5 * 2", "params": {}},
            "error": None,
            "private": False,
            "allow_execute_sql": True,
        },
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["query", "https://example.com", "hello"])
    assert result.exit_code == 0
    assert json.loads(result.output) == [{"5 * 2": 10}]


def test_aliases(mocker, tmpdir, httpx_mock):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    runner = CliRunner()
    result = runner.invoke(cli, ["alias", "list"])
    assert result.exit_code == 0
    assert result.output == ""

    result = runner.invoke(cli, ["alias", "add", "foo", "https://example.com/foo"])
    assert result.exit_code == 0
    assert result.output == ""

    result = runner.invoke(cli, ["alias", "list"])
    assert result.exit_code == 0
    assert result.output == "foo = https://example.com/foo\n"

    # --json mode:
    result = runner.invoke(cli, ["alias", "list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == {"foo": "https://example.com/foo"}

    # Check the aliases file
    aliases_file = pathlib.Path(tmpdir) / "aliases.json"
    assert json.loads(aliases_file.read_text()) == {"foo": "https://example.com/foo"}

    # Try a query against that alias
    httpx_mock.add_response(
        json={
            "ok": True,
            "database": "foo",
            "query_name": None,
            "rows": [{"11 * 3": 33}],
            "truncated": False,
            "columns": ["11 * 3"],
            "query": {"sql": "select 11 * 3", "params": {}},
            "error": None,
            "private": False,
            "allow_execute_sql": True,
        },
        status_code=200,
    )
    result = runner.invoke(cli, ["query", "foo", "select 11 * 3"])
    assert result.exit_code == 0
    assert json.loads(result.output) == [{"11 * 3": 33}]

    # Should have hit https://example.com/foo.json
    url = httpx_mock.get_request().url
    assert url == "https://example.com/foo.json?sql=select+11+%2A+3&_shape=objects"

    # Remove alias
    result = runner.invoke(cli, ["alias", "remove", "invalid"])
    assert result.exit_code == 1
    assert result.output == "Error: No such alias\n"

    result = runner.invoke(cli, ["alias", "remove", "foo"])
    assert result.exit_code == 0
    assert result.output == ""
    assert json.loads(aliases_file.read_text()) == {}
