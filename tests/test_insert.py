import asyncio
from collections import namedtuple
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


SIMPLE_CSV = "a,b,c\n1,2,3\n"


InsertTest = namedtuple(
    "InsertTest", "csv_data,cmd_args,expected_output,should_error,expected_table_json"
)


@pytest.mark.parametrize(
    "csv_data,cmd_args,expected_output,should_error,expected_table_json",
    (
        InsertTest(
            csv_data=SIMPLE_CSV,
            cmd_args=["--create"],
            expected_output="Inserting rows\n",
            should_error=False,
            expected_table_json=[{"rowid": 1, "a": 1, "b": 2, "c": 3}],
        ),
        InsertTest(
            csv_data=SIMPLE_CSV,
            cmd_args=[],
            expected_output="Inserting rows\nError: Table not found: table1\n",
            should_error=True,
            expected_table_json=None,
        ),
    ),
)
def test_insert_against_datasette(
    httpx_mock,
    tmpdir,
    csv_data,
    cmd_args,
    expected_output,
    should_error,
    expected_table_json,
):
    ds = Datasette(
        metadata={
            "permissions": {
                "create-table": {"id": "*"},
                "insert-row": {"id": "*"},
                "update-row": {"id": "*"},
            }
        }
    )
    db = ds.add_memory_database("data")
    # Drop all tables in the database each time, because in-memory
    # databases persist in between test runs
    drop_all_tables(db)

    token = ds.create_token("actor")

    loop = asyncio.get_event_loop()

    # These are useful with pytest --pdb to see what happened
    datasette_requests = []
    datasette_responses = []

    def custom_response(request: httpx.Request):
        # Need to run this in async loop, because dclient itself uses
        # sync HTTPX and not async HTTPX
        async def run():
            datasette_requests.append(request)
            response = await ds.client.request(
                request.method,
                request.url.path,
                json=json.loads(request.read()),
                headers=request.headers,
            )
            # Create a fresh response to avoid an error where stream has been consumed
            response = httpx.Response(
                status_code=response.status_code,
                headers=response.headers,
                content=response.content,
            )
            datasette_responses.append(response)
            return response

        return loop.run_until_complete(run())

    httpx_mock.add_callback(custom_response)

    path = pathlib.Path(tmpdir) / "data.csv"
    path.write_text(csv_data)
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
        ]
        + cmd_args,
        catch_exceptions=False,
    )
    if not should_error:
        assert result.exit_code == 0
    else:
        assert result.exit_code != 0
    assert result.output == expected_output

    if expected_table_json:

        async def fetch_table():
            response = await ds.client.get("/data/table1.json?_shape=array")
            return response

        response = loop.run_until_complete(fetch_table())
        assert response.json() == expected_table_json


def drop_all_tables(db):
    async def run():
        for table in await db.table_names():
            await db.execute_write("drop table {}".format(table))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
