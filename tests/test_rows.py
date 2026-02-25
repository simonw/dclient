from click.testing import CliRunner
from dclient.cli import cli
import json
import pathlib
import pytest


def test_rows_basic(httpx_mock):
    httpx_mock.add_response(
        json={
            "ok": True,
            "rows": [{"id": 1, "name": "Cleo", "age": 4}],
            "next": None,
        },
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["rows", "https://example.com/db", "creatures"])
    assert result.exit_code == 0
    assert json.loads(result.output) == [{"id": 1, "name": "Cleo", "age": 4}]
    request = httpx_mock.get_request()
    assert str(request.url) == "https://example.com/db/creatures.json?_shape=objects"


def test_rows_single_filter(httpx_mock):
    httpx_mock.add_response(
        json={"ok": True, "rows": [{"id": 2, "name": "Luna", "age": 7}]},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["rows", "https://example.com/db", "creatures", "-f", "age", "gte", "5"],
    )
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert "age__gte=5" in str(request.url)
    assert "_shape=objects" in str(request.url)


def test_rows_eq_maps_to_exact(httpx_mock):
    httpx_mock.add_response(
        json={"ok": True, "rows": [{"id": 1, "name": "Cleo"}]},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["rows", "https://example.com/db", "creatures", "-f", "name", "eq", "Cleo"],
    )
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert "name__exact=Cleo" in str(request.url)


def test_rows_multiple_filters(httpx_mock):
    httpx_mock.add_response(
        json={"ok": True, "rows": []},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "rows",
            "https://example.com/db",
            "creatures",
            "-f",
            "species",
            "in",
            "dog,cat",
            "-f",
            "age",
            "gt",
            "3",
        ],
    )
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    url_str = str(request.url)
    assert "species__in=" in url_str
    assert "age__gt=3" in url_str


def test_rows_where_clause(httpx_mock):
    httpx_mock.add_response(
        json={"ok": True, "rows": [{"id": 6}]},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["rows", "https://example.com/db", "creatures", "--where", "id > 5"],
    )
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert "_where=" in str(request.url)


def test_rows_multiple_where_clauses(httpx_mock):
    httpx_mock.add_response(
        json={"ok": True, "rows": []},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "rows",
            "https://example.com/db",
            "creatures",
            "--where",
            "id > 5",
            "--where",
            "age < 10",
        ],
    )
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    url_str = str(request.url)
    assert url_str.count("_where=") == 2


def test_rows_sort(httpx_mock):
    httpx_mock.add_response(
        json={"ok": True, "rows": [{"id": 1}]},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["rows", "https://example.com/db", "creatures", "--sort", "name"],
    )
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert "_sort=name" in str(request.url)


def test_rows_sort_desc(httpx_mock):
    httpx_mock.add_response(
        json={"ok": True, "rows": [{"id": 1}]},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["rows", "https://example.com/db", "creatures", "--sort-desc", "age"],
    )
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert "_sort_desc=age" in str(request.url)


def test_rows_sort_mutual_exclusion():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "rows",
            "https://example.com/db",
            "creatures",
            "--sort",
            "name",
            "--sort-desc",
            "age",
        ],
    )
    assert result.exit_code == 1
    assert "Cannot use both --sort and --sort-desc" in result.output


@pytest.mark.parametrize("with_token", (False, True))
def test_rows_with_token(httpx_mock, with_token):
    httpx_mock.add_response(
        json={"ok": True, "rows": [{"id": 1}]},
        status_code=200,
    )
    runner = CliRunner()
    args = ["rows", "https://example.com/db", "creatures"]
    if with_token:
        args.extend(["--token", "xyz"])
    result = runner.invoke(cli, args)
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    if with_token:
        assert request.headers["authorization"] == "Bearer xyz"
    else:
        assert "authorization" not in request.headers


def test_rows_http_error(httpx_mock):
    httpx_mock.add_response(
        json={"title": "Not Found", "error": "Table not found: creatures"},
        status_code=404,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["rows", "https://example.com/db", "creatures"])
    assert result.exit_code == 1
    assert "404 status code" in result.output
    assert "Table not found: creatures" in result.output


def test_rows_ok_false_error(httpx_mock):
    httpx_mock.add_response(
        json={"ok": False, "error": "Something went wrong"},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["rows", "https://example.com/db", "creatures"])
    assert result.exit_code == 1
    assert "Something went wrong" in result.output


def test_rows_with_alias(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    aliases_file = pathlib.Path(tmpdir) / "aliases.json"
    aliases_file.write_text(json.dumps({"content": "https://datasette.io/content"}))
    httpx_mock.add_response(
        json={"ok": True, "rows": [{"id": 1}]},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["rows", "content", "creatures"])
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.url.host == "datasette.io"
    assert request.url.path == "/content/creatures.json"


def test_rows_verbose(httpx_mock):
    httpx_mock.add_response(
        json={"ok": True, "rows": []},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["rows", "https://example.com/db", "creatures", "-v"],
    )
    assert result.exit_code == 0
    assert "creatures.json" in result.output


def test_rows_combined(httpx_mock):
    """Test filters, where, and sort all together."""
    httpx_mock.add_response(
        json={"ok": True, "rows": [{"id": 1, "name": "Cleo", "age": 4}]},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "rows",
            "https://example.com/db",
            "creatures",
            "-f",
            "species",
            "eq",
            "dog",
            "--where",
            "age > 2",
            "--sort-desc",
            "age",
        ],
    )
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    url_str = str(request.url)
    assert "species__exact=dog" in url_str
    assert "_where=" in url_str
    assert "_sort_desc=age" in url_str
