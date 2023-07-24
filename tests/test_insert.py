import asyncio
from click.testing import CliRunner
from datasette.app import Datasette
from dclient.cli import cli
import httpx
import json
import pathlib
import pytest


@pytest.fixture
def non_mocked_hosts():
    # This ensures httpx-mock will not affect Datasette's own
    # httpx calls made in the tests by datasette.client:
    return ["localhost"]


def test_insert_mocked(httpx_mock, tmpdir):
    httpx_mock.add_response(
        json={
            "ok": True,
            "database": "data",
            "table": "table1",
            "table_url": "http://datasette.example.com/data/table1",
            "table_api_url": "http://datasette.example.com/data/table1.json",
            "schema": "CREATE TABLE [table1] (...)",
            "row_count": 100,
        }
    )
    path = pathlib.Path(tmpdir) / "data.csv"
    path.write_text("a,b,c\n1,2,3\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "insert",
            "https://datasette.example.com/data",
            "table1",
            str(path),
            "--csv",
            "--token",
            "x",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output == "Inserting rows\n"
    request = httpx_mock.get_request()
    assert request.headers["authorization"] == "Bearer x"
    assert json.loads(request.read()) == {"rows": [{"a": 1, "b": 2, "c": 3}]}


def test_insert_against_datasette(httpx_mock, tmpdir):
    ds = Datasette(
        metadata={
            "permissions": {
                "create-table": {"id": "*"},
                "insert-row": {"id": "*"},
                "update-row": {"id": "*"},
            }
        }
    )
    ds.add_memory_database("data")

    token = ds.create_token("actor")

    loop = asyncio.get_event_loop()

    def custom_response(request: httpx.Request):
        # Need to run this in async loop, because dclient itself uses
        # sync HTTPX and not async HTTPX
        async def run():
            response = await ds.client.request(
                request.method,
                request.url.path,
                json=json.loads(request.read()),
                headers=request.headers,
            )
            # Create a fresh response to avoid an error where stream has been consumed
            return httpx.Response(
                status_code=response.status_code,
                headers=response.headers,
                content=response.content,
            )

        return loop.run_until_complete(run())

    httpx_mock.add_callback(custom_response)

    path = pathlib.Path(tmpdir) / "data.csv"
    path.write_text("a,b,c\n1,2,3\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "insert",
            "http://datasette.example.com/data",
            "table1",
            str(path),
            "--csv",
            "--token",
            token,
            "--create",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    # Datasette should have the new rows
    async def fetch_table():
        response = await ds.client.get("/data/table1.json?_shape=array")
        return response

    response = loop.run_until_complete(fetch_table())
    assert response.json() == [{"rowid": 1, "a": 1, "b": 2, "c": 3}]
