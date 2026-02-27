"""Tests for the rows command."""

from click.testing import CliRunner
from dclient.cli import cli
import json
import pathlib

TABLE_RESPONSE = {
    "ok": True,
    "rows": [
        {"id": 1, "name": "Cleo", "age": 5},
        {"id": 2, "name": "Pancakes", "age": 3},
        {"id": 3, "name": "Fido", "age": 7},
    ],
    "columns": ["id", "name", "age"],
    "next": None,
    "next_url": None,
}


def _invoke(httpx_mock, extra_args=None, response=None):
    httpx_mock.add_response(json=response or TABLE_RESPONSE, status_code=200)
    runner = CliRunner()
    args = ["rows", "fixtures", "dogs", "-i", "https://example.com"]
    if extra_args:
        args.extend(extra_args)
    return runner.invoke(cli, args)


# -- basic usage --


def test_rows_default_json(httpx_mock):
    result = _invoke(httpx_mock)
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert len(data) == 3
    assert data[0]["name"] == "Cleo"
    # Verify request URL
    request = httpx_mock.get_request()
    assert request.url.path == "/fixtures/dogs.json"
    assert "_shape" in dict(request.url.params)
    assert dict(request.url.params)["_shape"] == "objects"


def test_rows_table_format(httpx_mock):
    result = _invoke(httpx_mock, ["-t"])
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert len(lines) == 5  # header + separator + 3 data rows
    assert "Cleo" in lines[2]
    assert "Pancakes" in lines[3]


def test_rows_csv(httpx_mock):
    result = _invoke(httpx_mock, ["--csv"])
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert lines[0] == "id,name,age"
    assert lines[1] == "1,Cleo,5"


def test_rows_nl(httpx_mock):
    result = _invoke(httpx_mock, ["--nl"])
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert json.loads(lines[0]) == {"id": 1, "name": "Cleo", "age": 5}


# -- single argument uses default database --


def test_rows_single_arg_uses_default_database(httpx_mock, mocker, tmpdir):
    """dclient rows tablename uses default database."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    config_file = pathlib.Path(tmpdir) / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "default_instance": "prod",
                "instances": {
                    "prod": {
                        "url": "https://prod.example.com",
                        "default_database": "data",
                    }
                },
            }
        )
    )
    httpx_mock.add_response(json=TABLE_RESPONSE, status_code=200)
    runner = CliRunner()
    result = runner.invoke(cli, ["rows", "dogs"])
    assert result.exit_code == 0, result.output
    request = httpx_mock.get_request()
    assert request.url.host == "prod.example.com"
    assert request.url.path == "/data/dogs.json"


def test_rows_single_arg_no_default_database_errors(mocker, tmpdir):
    """dclient rows tablename without default database gives error."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    config_file = pathlib.Path(tmpdir) / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "default_instance": "prod",
                "instances": {
                    "prod": {
                        "url": "https://prod.example.com",
                        "default_database": None,
                    }
                },
            }
        )
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["rows", "dogs"])
    assert result.exit_code == 1
    assert "No database specified" in result.output


# -- filters --


def test_rows_filter_eq(httpx_mock):
    result = _invoke(httpx_mock, ["-f", "name", "eq", "Cleo"])
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    params = dict(request.url.params)
    assert params["name__exact"] == "Cleo"


def test_rows_filter_gt(httpx_mock):
    result = _invoke(httpx_mock, ["--filter", "age", "gt", "3"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["age__gt"] == "3"


def test_rows_filter_gte(httpx_mock):
    result = _invoke(httpx_mock, ["-f", "age", "gte", "5"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["age__gte"] == "5"


def test_rows_filter_lt(httpx_mock):
    result = _invoke(httpx_mock, ["-f", "age", "lt", "5"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["age__lt"] == "5"


def test_rows_filter_lte(httpx_mock):
    result = _invoke(httpx_mock, ["-f", "age", "lte", "5"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["age__lte"] == "5"


def test_rows_filter_not(httpx_mock):
    result = _invoke(httpx_mock, ["-f", "name", "not", "Cleo"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["name__not"] == "Cleo"


def test_rows_filter_contains(httpx_mock):
    result = _invoke(httpx_mock, ["-f", "name", "contains", "leo"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["name__contains"] == "leo"


def test_rows_filter_like(httpx_mock):
    result = _invoke(httpx_mock, ["-f", "name", "like", "%leo%"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["name__like"] == "%leo%"


def test_rows_filter_startswith(httpx_mock):
    result = _invoke(httpx_mock, ["-f", "name", "startswith", "Cl"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["name__startswith"] == "Cl"


def test_rows_filter_endswith(httpx_mock):
    result = _invoke(httpx_mock, ["-f", "name", "endswith", "eo"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["name__endswith"] == "eo"


def test_rows_filter_glob(httpx_mock):
    result = _invoke(httpx_mock, ["-f", "name", "glob", "C*"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["name__glob"] == "C*"


def test_rows_filter_isnull(httpx_mock):
    result = _invoke(httpx_mock, ["-f", "name", "isnull", "1"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["name__isnull"] == "1"


def test_rows_filter_notnull(httpx_mock):
    result = _invoke(httpx_mock, ["-f", "name", "notnull", "1"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["name__notnull"] == "1"


def test_rows_multiple_filters(httpx_mock):
    result = _invoke(httpx_mock, ["-f", "name", "eq", "Cleo", "-f", "age", "gte", "3"])
    assert result.exit_code == 0
    params = list(httpx_mock.get_request().url.params.multi_items())
    param_dict = {k: v for k, v in params}
    assert param_dict["name__exact"] == "Cleo"
    assert param_dict["age__gte"] == "3"


def test_rows_custom_filter_op_passthrough(httpx_mock):
    """Unknown ops are passed through to Datasette, supporting plugin-added filters."""
    result = _invoke(httpx_mock, ["-f", "name", "custom_plugin_op", "x"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["name__custom_plugin_op"] == "x"


# -- sorting --


def test_rows_sort(httpx_mock):
    result = _invoke(httpx_mock, ["--sort", "age"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["_sort"] == "age"


def test_rows_sort_desc(httpx_mock):
    result = _invoke(httpx_mock, ["--sort-desc", "age"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["_sort_desc"] == "age"


# -- column selection --


def test_rows_col(httpx_mock):
    result = _invoke(httpx_mock, ["--col", "name", "--col", "age"])
    assert result.exit_code == 0
    params = list(httpx_mock.get_request().url.params.multi_items())
    col_params = [v for k, v in params if k == "_col"]
    assert col_params == ["name", "age"]


def test_rows_nocol(httpx_mock):
    result = _invoke(httpx_mock, ["--nocol", "id"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["_nocol"] == "id"


# -- search --


def test_rows_search(httpx_mock):
    result = _invoke(httpx_mock, ["--search", "pancakes"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["_search"] == "pancakes"


# -- size --


def test_rows_size(httpx_mock):
    result = _invoke(httpx_mock, ["--size", "10"])
    assert result.exit_code == 0
    assert dict(httpx_mock.get_request().url.params)["_size"] == "10"


# -- limit --


def test_rows_limit(httpx_mock):
    response = {
        "ok": True,
        "rows": [{"id": 1}, {"id": 2}, {"id": 3}],
        "columns": ["id"],
        "next": None,
    }
    result = _invoke(httpx_mock, ["--limit", "2"], response=response)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


# -- pagination with --all --


def test_rows_all_pagination(httpx_mock):
    page1 = {
        "ok": True,
        "rows": [{"id": 1}, {"id": 2}],
        "columns": ["id"],
        "next": "2",
        "next_url": "https://example.com/fixtures/dogs.json?_next=2&_shape=objects",
    }
    page2 = {
        "ok": True,
        "rows": [{"id": 3}],
        "columns": ["id"],
        "next": None,
        "next_url": None,
    }
    httpx_mock.add_response(json=page1, status_code=200)
    httpx_mock.add_response(json=page2, status_code=200)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["rows", "fixtures", "dogs", "-i", "https://example.com", "--all"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 3
    assert [r["id"] for r in data] == [1, 2, 3]


def test_rows_all_with_limit(httpx_mock):
    page1 = {
        "ok": True,
        "rows": [{"id": 1}, {"id": 2}],
        "columns": ["id"],
        "next": "2",
        "next_url": "https://example.com/fixtures/dogs.json?_next=2&_shape=objects",
    }
    page2 = {
        "ok": True,
        "rows": [{"id": 3}, {"id": 4}],
        "columns": ["id"],
        "next": None,
    }
    httpx_mock.add_response(json=page1, status_code=200)
    httpx_mock.add_response(json=page2, status_code=200)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "rows",
            "fixtures",
            "dogs",
            "-i",
            "https://example.com",
            "--all",
            "--limit",
            "3",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 3


def test_rows_no_all_ignores_next(httpx_mock):
    """Without --all, pagination is not followed even if next is present."""
    response = {
        "ok": True,
        "rows": [{"id": 1}, {"id": 2}],
        "columns": ["id"],
        "next": "2",
        "next_url": "https://example.com/fixtures/dogs.json?_next=2&_shape=objects",
    }
    result = _invoke(httpx_mock, response=response)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2  # only first page


# -- error handling --


def test_rows_api_error(httpx_mock):
    httpx_mock.add_response(
        json={"ok": False, "error": "Table not found: dogs"},
        status_code=404,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["rows", "fixtures", "dogs", "-i", "https://example.com"],
    )
    assert result.exit_code == 1
    assert "Table not found" in result.output


# -- uses default instance --


def test_rows_default_instance(httpx_mock, mocker, tmpdir):
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
    httpx_mock.add_response(json=TABLE_RESPONSE, status_code=200)
    runner = CliRunner()
    result = runner.invoke(cli, ["rows", "data", "dogs"])
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.url.host == "prod.example.com"
    assert request.url.path == "/data/dogs.json"
