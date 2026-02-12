"""Tests for new T1 and T2 commands: databases, tables, schema, rows, get,
upsert, update, delete, drop, create-table."""

import asyncio
import json
import pathlib

import pytest
from click.testing import CliRunner
from datasette.app import Datasette

from dclient.cli import cli


@pytest.fixture
def ds():
    """Create a Datasette instance with a memory database and sample data."""
    datasette = Datasette(
        config={
            "permissions": {
                "create-table": {"id": "*"},
                "insert-row": {"id": "*"},
                "update-row": {"id": "*"},
                "delete-row": {"id": "*"},
                "drop-table": {"id": "*"},
                "alter-table": {"id": "*"},
            }
        }
    )
    db = datasette.add_memory_database("data")
    loop = asyncio.get_event_loop()

    async def setup():
        # Drop all tables first
        for table in await db.table_names():
            await db.execute_write("drop table [{}]".format(table))
        await db.execute_write(
            "create table dogs (id integer primary key, name text, age integer)"
        )
        await db.execute_write(
            "insert into dogs (id, name, age) values (1, 'Cleo', 5), (2, 'Pancakes', 3), (3, 'Fido', 7)"
        )

    loop.run_until_complete(setup())
    return datasette, db, loop


@pytest.fixture
def token(ds):
    datasette, _, _ = ds
    return datasette.create_token("actor")


def _mock_datasette(httpx_mock, ds):
    """Set up httpx_mock to route requests through the Datasette instance."""
    datasette, _, loop = ds

    def custom_response(request):
        async def run():
            method = request.method
            url_path = request.url.raw_path.decode()
            if method == "GET":
                response = await datasette.client.get(
                    url_path, headers=request.headers
                )
            else:
                content = request.read()
                try:
                    body = json.loads(content) if content else {}
                except json.JSONDecodeError:
                    body = {}
                response = await datasette.client.request(
                    method, url_path, json=body, headers=request.headers
                )
            import httpx as httpx_lib

            return httpx_lib.Response(
                status_code=response.status_code,
                headers=response.headers,
                content=response.content,
            )

        return loop.run_until_complete(run())

    httpx_mock.add_callback(custom_response, is_optional=True)


# --- databases command ---


def test_databases(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(cli, ["databases", "http://localhost/", "--token", token])
    assert result.exit_code == 0
    data = json.loads(result.output)
    names = [d["name"] for d in data]
    assert "data" in names


def test_databases_table_format(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["databases", "http://localhost/", "--token", token, "--table"]
    )
    assert result.exit_code == 0
    assert "name" in result.output
    assert "data" in result.output


# --- tables command ---


def test_tables(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(cli, ["tables", "http://localhost/data", "--token", token])
    assert result.exit_code == 0
    data = json.loads(result.output)
    table_names = [t["name"] for t in data]
    assert "dogs" in table_names


def test_tables_table_format(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["tables", "http://localhost/data", "--token", token, "--table"]
    )
    assert result.exit_code == 0
    assert "dogs" in result.output


# --- schema command ---


def test_schema(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(cli, ["schema", "http://localhost/data", "--token", token])
    assert result.exit_code == 0
    assert "CREATE TABLE" in result.output
    assert "dogs" in result.output


# --- rows command ---


def test_rows_basic(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["rows", "http://localhost/data/dogs", "--token", token]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 3
    names = [r["name"] for r in data]
    assert "Cleo" in names


def test_rows_with_filter(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["rows", "http://localhost/data/dogs", "--token", token, "-w", "age__gt=4"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    for row in data:
        assert row["age"] > 4


def test_rows_with_sort(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["rows", "http://localhost/data/dogs", "--token", token, "--sort", "name"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    names = [r["name"] for r in data]
    assert names == sorted(names)


def test_rows_with_sort_desc(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "rows",
            "http://localhost/data/dogs",
            "--token",
            token,
            "--sort-desc",
            "age",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    ages = [r["age"] for r in data]
    assert ages == sorted(ages, reverse=True)


def test_rows_csv(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["rows", "http://localhost/data/dogs", "--token", token, "--csv"]
    )
    assert result.exit_code == 0
    assert "id,name,age" in result.output
    assert "Cleo" in result.output


def test_rows_nl(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["rows", "http://localhost/data/dogs", "--token", token, "--nl"]
    )
    assert result.exit_code == 0
    lines = [l for l in result.output.strip().split("\n") if l]
    for line in lines:
        parsed = json.loads(line)
        assert "name" in parsed


def test_rows_table_format(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["rows", "http://localhost/data/dogs", "--token", token, "--table"]
    )
    assert result.exit_code == 0
    assert "id" in result.output
    assert "name" in result.output
    assert "Cleo" in result.output
    # Should have header separator
    assert "---" in result.output


def test_rows_with_limit(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["rows", "http://localhost/data/dogs", "--token", token, "--limit", "2"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


def test_rows_with_columns(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["rows", "http://localhost/data/dogs", "--token", token, "--col", "name"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    for row in data:
        assert "name" in row


# --- get command ---


def test_get(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["get", "http://localhost/data/dogs", "1", "--token", token]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["name"] == "Cleo"
    assert data["id"] == 1


# --- upsert command ---


def test_upsert(httpx_mock, ds, token, tmpdir):
    _mock_datasette(httpx_mock, ds)
    # Upsert: update Cleo's age and add a new dog
    data = json.dumps([
        {"id": 1, "name": "Cleo", "age": 6},
        {"id": 4, "name": "Muffin", "age": 2},
    ])
    path = pathlib.Path(tmpdir) / "upsert.json"
    path.write_text(data)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "upsert",
            "http://localhost/data",
            "dogs",
            str(path),
            "--json",
            "--token",
            token,
        ],
    )
    assert result.exit_code == 0, result.output

    # Verify
    datasette, _, loop = ds

    async def check():
        r = await datasette.client.get("/data/dogs.json?_shape=array")
        return r.json()

    rows = loop.run_until_complete(check())
    names = {r["name"]: r["age"] for r in rows}
    assert names["Cleo"] == 6  # updated
    assert names["Muffin"] == 2  # inserted


# --- update command ---


def test_update(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "update",
            "http://localhost/data/dogs",
            "1",
            "name=Rex",
            "age=10",
            "--token",
            token,
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data.get("ok") is True

    # Verify the update
    datasette, _, loop = ds

    async def check():
        r = await datasette.client.get("/data/dogs/1.json?_shape=objects")
        return r.json()

    row_data = loop.run_until_complete(check())
    row = row_data["rows"][0]
    assert row["name"] == "Rex"
    assert row["age"] == 10


# --- delete command ---


def test_delete(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "delete",
            "http://localhost/data/dogs",
            "3",
            "--yes",
            "--token",
            token,
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data.get("ok") is True

    # Verify deletion
    datasette, _, loop = ds

    async def check():
        r = await datasette.client.get("/data/dogs.json?_shape=array")
        return r.json()

    rows = loop.run_until_complete(check())
    ids = [r["id"] for r in rows]
    assert 3 not in ids
    assert len(rows) == 2


# --- drop command ---


def test_drop(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["drop", "http://localhost/data/dogs", "--yes", "--token", token],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data.get("ok") is True

    # Verify table is gone
    datasette, db, loop = ds

    async def check():
        return await db.table_names()

    tables = loop.run_until_complete(check())
    assert "dogs" not in tables


# --- create-table command ---


def test_create_table(httpx_mock, ds, token):
    _mock_datasette(httpx_mock, ds)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create-table",
            "http://localhost/data",
            "cats",
            "--column",
            "id",
            "integer",
            "--column",
            "name",
            "text",
            "--pk",
            "id",
            "--token",
            token,
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data.get("ok") is True

    # Verify table exists
    datasette, db, loop = ds

    async def check():
        return await db.table_names()

    tables = loop.run_until_complete(check())
    assert "cats" in tables


# --- output format tests for query ---


SAMPLE_QUERY_RESPONSE = {
    "ok": True,
    "database": "data",
    "rows": [
        {"id": 1, "name": "Cleo", "age": 5},
        {"id": 2, "name": "Pancakes", "age": 3},
        {"id": 3, "name": "Fido", "age": 7},
    ],
    "truncated": False,
    "columns": ["id", "name", "age"],
}


def test_query_csv(httpx_mock):
    httpx_mock.add_response(json=SAMPLE_QUERY_RESPONSE, status_code=200)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["query", "https://example.com/data", "select * from dogs", "--csv"]
    )
    assert result.exit_code == 0
    assert "id,name,age" in result.output
    assert "Cleo" in result.output


def test_query_nl(httpx_mock):
    httpx_mock.add_response(json=SAMPLE_QUERY_RESPONSE, status_code=200)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["query", "https://example.com/data", "select * from dogs", "--nl"]
    )
    assert result.exit_code == 0
    lines = [l for l in result.output.strip().split("\n") if l]
    assert len(lines) == 3
    first = json.loads(lines[0])
    assert first["name"] == "Cleo"


def test_query_table_format(httpx_mock):
    httpx_mock.add_response(json=SAMPLE_QUERY_RESPONSE, status_code=200)
    runner = CliRunner()
    result = runner.invoke(
        cli, ["query", "https://example.com/data", "select * from dogs", "--table"]
    )
    assert result.exit_code == 0
    assert "Cleo" in result.output
    assert "---" in result.output
