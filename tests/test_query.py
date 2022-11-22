from click.testing import CliRunner
from dclient.cli import cli
import json


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
