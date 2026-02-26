"""Tests for v2 commands: databases, tables, plugins, schema, default_query, upsert."""

from click.testing import CliRunner
from dclient.cli import cli
import json
import pathlib
import pytest

# -- databases command --


def test_databases_json(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={
            "databases": [
                {"name": "main", "tables_count": 12},
                {"name": "extra", "tables_count": 3},
            ]
        },
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["databases", "-i", "https://example.com", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2
    assert data[0]["name"] == "main"


def test_databases_plain(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={
            "databases": [
                {"name": "main", "tables_count": 12},
                {"name": "extra", "tables_count": 3},
            ]
        },
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["databases", "-i", "https://example.com"])
    assert result.exit_code == 0
    assert "main\n" in result.output
    assert "extra\n" in result.output


def test_databases_url(httpx_mock, mocker, tmpdir):
    """databases command hits /.json on the instance."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={"databases": [{"name": "db1"}]},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["databases", "-i", "https://example.com"])
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.url.path == "/.json"


# -- tables command --


def test_tables_json(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={
            "tables": [
                {"name": "facetable", "count": 15, "hidden": False},
                {"name": "facet_cities", "count": 4, "hidden": False},
            ],
            "views": [],
        },
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tables", "-i", "https://example.com", "-d", "fixtures", "--json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


def test_tables_plain(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={
            "tables": [
                {"name": "facetable", "count": 15, "hidden": False},
            ],
            "views": [],
        },
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli, ["tables", "-i", "https://example.com", "-d", "fixtures"]
    )
    assert result.exit_code == 0
    assert "facetable" in result.output
    assert "15 rows" in result.output


def test_tables_url(httpx_mock, mocker, tmpdir):
    """tables command hits /<database>.json."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={"tables": [], "views": []},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli, ["tables", "-i", "https://example.com", "-d", "fixtures"]
    )
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.url.path == "/fixtures.json"


def test_tables_with_views(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={
            "tables": [{"name": "t1", "count": 5, "hidden": False}],
            "views": [{"name": "v1"}],
        },
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli, ["tables", "-i", "https://example.com", "-d", "db", "--views"]
    )
    assert result.exit_code == 0
    assert "t1" in result.output
    assert "v1" in result.output


def test_tables_views_only(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={
            "tables": [{"name": "t1", "count": 5, "hidden": False}],
            "views": [{"name": "v1"}],
        },
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["tables", "-i", "https://example.com", "-d", "db", "--views-only"],
    )
    assert result.exit_code == 0
    assert "t1" not in result.output
    assert "v1" in result.output


def test_tables_hidden(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={
            "tables": [
                {"name": "visible", "count": 5, "hidden": False},
                {"name": "hidden_t", "count": 2, "hidden": True},
            ],
            "views": [],
        },
        status_code=200,
    )
    runner = CliRunner()
    # Without --hidden
    result = runner.invoke(cli, ["tables", "-i", "https://example.com", "-d", "db"])
    assert "visible" in result.output
    assert "hidden_t" not in result.output

    # With --hidden
    httpx_mock.add_response(
        json={
            "tables": [
                {"name": "visible", "count": 5, "hidden": False},
                {"name": "hidden_t", "count": 2, "hidden": True},
            ],
            "views": [],
        },
        status_code=200,
    )
    result = runner.invoke(
        cli,
        ["tables", "-i", "https://example.com", "-d", "db", "--hidden"],
    )
    assert "visible" in result.output
    assert "hidden_t" in result.output


# -- plugins command --


def test_plugins_json(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json=[
            {"name": "datasette-files", "version": "0.3.1"},
            {"name": "datasette-auth-tokens", "version": "0.4"},
        ],
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["plugins", "-i", "https://example.com", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


def test_plugins_plain(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json=[
            {"name": "datasette-files", "version": "0.3.1"},
            {"name": "datasette-auth-tokens", "version": "0.4"},
        ],
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["plugins", "-i", "https://example.com"])
    assert result.exit_code == 0
    assert "datasette-files\n" in result.output
    assert "datasette-auth-tokens\n" in result.output


def test_plugins_url(httpx_mock, mocker, tmpdir):
    """plugins command hits /-/plugins.json."""
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(json=[], status_code=200)
    runner = CliRunner()
    result = runner.invoke(cli, ["plugins", "-i", "https://example.com"])
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.url.path == "/-/plugins.json"


# -- schema command --


def test_schema_all_tables(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    full_schema = (
        "CREATE TABLE users (id integer primary key, name text);\n"
        "CREATE VIEW user_count AS SELECT count(*) FROM users;"
    )
    httpx_mock.add_response(
        json={"database": "main", "schema": full_schema},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["schema", "-i", "https://example.com", "-d", "main"])
    assert result.exit_code == 0
    assert "CREATE TABLE users" in result.output
    assert "CREATE VIEW user_count" in result.output
    request = httpx_mock.get_request()
    assert request.url.path == "/main/-/schema.json"


def test_schema_specific_table(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={
            "database": "main",
            "table": "users",
            "schema": "CREATE TABLE users (id integer primary key, name text)",
        },
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli, ["schema", "users", "-i", "https://example.com", "-d", "main"]
    )
    assert result.exit_code == 0
    assert "CREATE TABLE users" in result.output
    request = httpx_mock.get_request()
    assert request.url.path == "/main/users/-/schema.json"


def test_schema_json(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    full_schema = "CREATE TABLE users (id integer primary key);"
    httpx_mock.add_response(
        json={"database": "main", "schema": full_schema},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["schema", "-i", "https://example.com", "-d", "main", "--json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "schema" in data


# -- default_query (bare SQL shortcut) --


def test_default_query_with_defaults(httpx_mock, mocker, tmpdir):
    """Bare SQL uses default instance + default database."""
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
    httpx_mock.add_response(
        json={
            "ok": True,
            "rows": [{"count(*)": 42}],
            "columns": ["count(*)"],
        },
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["select count(*) from users"])
    assert result.exit_code == 0
    assert json.loads(result.output) == [{"count(*)": 42}]
    request = httpx_mock.get_request()
    assert request.url.host == "prod.example.com"
    assert request.url.path == "/main.json"


def test_default_query_with_database_override(httpx_mock, mocker, tmpdir):
    """Bare SQL with -d flag overrides the database."""
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
    httpx_mock.add_response(
        json={
            "ok": True,
            "rows": [{"count(*)": 100}],
            "columns": ["count(*)"],
        },
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["select count(*) from events", "-d", "analytics"])
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.url.path == "/analytics.json"


def test_default_query_with_instance_override(httpx_mock, mocker, tmpdir):
    """Bare SQL with -i flag overrides the instance."""
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
                    },
                    "staging": {
                        "url": "https://staging.example.com",
                        "default_database": "main",
                    },
                },
            }
        )
    )
    httpx_mock.add_response(
        json={
            "ok": True,
            "rows": [{"count(*)": 5}],
            "columns": ["count(*)"],
        },
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["select count(*) from users", "-i", "staging"])
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.url.host == "staging.example.com"


def test_default_query_no_database_error(mocker, tmpdir):
    """Bare SQL without a default database gives an error."""
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
    result = runner.invoke(cli, ["select 1"])
    assert result.exit_code == 1
    assert "No database specified" in result.output


# -- upsert command --


def test_upsert_mocked(httpx_mock, tmpdir, mocker):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={
            "ok": True,
        }
    )
    path = pathlib.Path(tmpdir) / "data.csv"
    path.write_text("a,b,c\n1,2,3\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "upsert",
            "data",
            "table1",
            str(path),
            "--csv",
            "--token",
            "x",
            "-i",
            "https://datasette.example.com",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    request = httpx_mock.get_request()
    assert request.headers["authorization"] == "Bearer x"
    # Should hit /-/upsert endpoint
    assert "/table1/-/upsert" in str(request.url)
    assert json.loads(request.read()) == {"rows": [{"a": 1, "b": 2, "c": 3}]}


# -- auth status command --


def test_auth_status(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={"actor": {"id": "root"}},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli, ["auth", "status", "-i", "https://example.com", "--token", "tok"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["actor"]["id"] == "root"
    request = httpx_mock.get_request()
    assert request.url.path == "/-/actor.json"


# -- actor command --


def test_actor_with_instance_flag(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={"actor": {"id": "root"}},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli, ["actor", "-i", "https://example.com", "--token", "tok"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["actor"]["id"] == "root"
    request = httpx_mock.get_request()
    assert request.url.path == "/-/actor.json"
    assert request.headers["authorization"] == "Bearer tok"


# -- get command --


def test_get_command(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={"hello": "world"},
        status_code=200,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["get", "/-/plugins.json", "-i", "https://example.com"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == {"hello": "world"}
    request = httpx_mock.get_request()
    assert request.url.path == "/-/plugins.json"


# -- instances command --


def test_instances_plain(mocker, tmpdir):
    config_dir = pathlib.Path(tmpdir)
    mocker.patch("dclient.cli.get_config_dir", return_value=config_dir)
    (config_dir / "config.json").write_text(
        json.dumps(
            {
                "default_instance": "prod",
                "instances": {
                    "prod": {
                        "url": "https://prod.example.com",
                        "default_database": "main",
                    },
                    "staging": {
                        "url": "https://staging.example.com",
                        "default_database": None,
                    },
                },
            }
        )
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["instances"])
    assert result.exit_code == 0
    assert "* prod = https://prod.example.com (db: main)" in result.output
    assert "  staging = https://staging.example.com" in result.output


def test_instances_json(mocker, tmpdir):
    config_dir = pathlib.Path(tmpdir)
    mocker.patch("dclient.cli.get_config_dir", return_value=config_dir)
    (config_dir / "config.json").write_text(
        json.dumps(
            {
                "default_instance": "prod",
                "instances": {
                    "prod": {
                        "url": "https://prod.example.com",
                        "default_database": "main",
                    },
                },
            }
        )
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["instances", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "prod" in data["instances"]
    assert data["default_instance"] == "prod"


def test_instances_empty(mocker, tmpdir):
    config_dir = pathlib.Path(tmpdir)
    mocker.patch("dclient.cli.get_config_dir", return_value=config_dir)
    runner = CliRunner()
    result = runner.invoke(cli, ["instances"])
    assert result.exit_code == 0
    assert result.output.strip() == ""
