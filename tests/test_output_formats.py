"""Tests for multiple output formats on the query and default_query commands."""

from click.testing import CliRunner
from dclient.cli import cli
import json
import pathlib

QUERY_RESPONSE = {
    "ok": True,
    "database": "fixtures",
    "query_name": None,
    "rows": [
        {"id": 1, "name": "Cleo", "age": 5},
        {"id": 2, "name": "Pancakes", "age": 3},
    ],
    "truncated": False,
    "columns": ["id", "name", "age"],
    "query": {"sql": "select * from dogs", "params": {}},
    "error": None,
    "private": False,
    "allow_execute_sql": True,
}


def _mock_and_invoke(httpx_mock, extra_args=None):
    httpx_mock.add_response(json=QUERY_RESPONSE, status_code=200)
    runner = CliRunner()
    args = ["query", "fixtures", "select * from dogs", "-i", "https://example.com"]
    if extra_args:
        args.extend(extra_args)
    return runner.invoke(cli, args)


# -- query --csv --


def test_query_csv(httpx_mock):
    result = _mock_and_invoke(httpx_mock, ["--csv"])
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert lines[0] == "id,name,age"
    assert lines[1] == "1,Cleo,5"
    assert lines[2] == "2,Pancakes,3"


# -- query --tsv --


def test_query_tsv(httpx_mock):
    result = _mock_and_invoke(httpx_mock, ["--tsv"])
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert lines[0] == "id\tname\tage"
    assert lines[1] == "1\tCleo\t5"
    assert lines[2] == "2\tPancakes\t3"


# -- query --nl --


def test_query_nl(httpx_mock):
    result = _mock_and_invoke(httpx_mock, ["--nl"])
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"id": 1, "name": "Cleo", "age": 5}
    assert json.loads(lines[1]) == {"id": 2, "name": "Pancakes", "age": 3}


# -- query --table --


def test_query_table(httpx_mock):
    result = _mock_and_invoke(httpx_mock, ["--table"])
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    # Should have a header row, a separator row, and 2 data rows
    assert len(lines) == 4
    # Header should contain column names
    assert "id" in lines[0]
    assert "name" in lines[0]
    assert "age" in lines[0]
    # Data rows should contain values
    assert "Cleo" in lines[2]
    assert "Pancakes" in lines[3]


# -- query -t shortcut for --table --


def test_query_table_shortcut(httpx_mock):
    result = _mock_and_invoke(httpx_mock, ["-t"])
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert len(lines) == 4
    assert "Cleo" in lines[2]


# -- default JSON (no flag) stays the same --


def test_query_default_json(httpx_mock):
    result = _mock_and_invoke(httpx_mock)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == [
        {"id": 1, "name": "Cleo", "age": 5},
        {"id": 2, "name": "Pancakes", "age": 3},
    ]


# -- default_query also supports output formats --


def _mock_default_query(httpx_mock, mocker, tmpdir, extra_args=None):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
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
    httpx_mock.add_response(json=QUERY_RESPONSE, status_code=200)
    runner = CliRunner()
    args = ["select * from dogs"]
    if extra_args:
        args.extend(extra_args)
    return runner.invoke(cli, args)


def test_default_query_csv(httpx_mock, mocker, tmpdir):
    result = _mock_default_query(httpx_mock, mocker, tmpdir, ["--csv"])
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert lines[0] == "id,name,age"
    assert lines[1] == "1,Cleo,5"


def test_default_query_table(httpx_mock, mocker, tmpdir):
    result = _mock_default_query(httpx_mock, mocker, tmpdir, ["--table"])
    assert result.exit_code == 0
    assert "Cleo" in result.output
    assert "Pancakes" in result.output
    lines = result.output.strip().split("\n")
    assert len(lines) == 4


def test_default_query_nl(httpx_mock, mocker, tmpdir):
    result = _mock_default_query(httpx_mock, mocker, tmpdir, ["--nl"])
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert json.loads(lines[0]) == {"id": 1, "name": "Cleo", "age": 5}


# -- edge cases --


def test_query_csv_with_commas_in_values(httpx_mock):
    httpx_mock.add_response(
        json={
            "ok": True,
            "rows": [{"name": "Smith, John", "note": 'He said "hi"'}],
            "columns": ["name", "note"],
        },
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "query",
            "db",
            "select * from t",
            "-i",
            "https://example.com",
            "--csv",
        ],
    )
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert lines[0] == "name,note"
    # CSV should properly quote fields with commas/quotes
    assert '"Smith, John"' in lines[1]


def test_query_table_empty_results(httpx_mock):
    httpx_mock.add_response(
        json={
            "ok": True,
            "rows": [],
            "columns": ["id", "name"],
        },
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "query",
            "db",
            "select * from t",
            "-i",
            "https://example.com",
            "--table",
        ],
    )
    assert result.exit_code == 0


def test_query_csv_empty_results(httpx_mock):
    httpx_mock.add_response(
        json={
            "ok": True,
            "rows": [],
            "columns": ["id", "name"],
        },
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "query",
            "db",
            "select * from t",
            "-i",
            "https://example.com",
            "--csv",
        ],
    )
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert lines[0] == "id,name"
    assert len(lines) == 1  # header only, no data rows


def test_query_nl_empty_results(httpx_mock):
    httpx_mock.add_response(
        json={
            "ok": True,
            "rows": [],
            "columns": ["id", "name"],
        },
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "query",
            "db",
            "select * from t",
            "-i",
            "https://example.com",
            "--nl",
        ],
    )
    assert result.exit_code == 0
    assert result.output.strip() == ""
