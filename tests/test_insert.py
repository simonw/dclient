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
def assert_all_responses_were_requested() -> bool:
    return False


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
SIMPLE_TSV = "a\tb\tc\n1\t2\t3\n"
SIMPLE_JSON = json.dumps(
    [
        {
            "a": 1,
            "b": 2,
            "c": 3,
        }
    ]
)
SIMPLE_JSON_NL = '{"a": 1, "b": 2, "c": 3}\n'
LATIN1_CSV = (
    b"date,name,latitude,longitude\n"
    b"2020-01-01,Barra da Lagoa,-27.574,-48.422\n"
    b"2020-03-04,S\xe3o Paulo,-23.561,-46.645\n"
    b"2020-04-05,Salta,-24.793:-65.408"
)


InsertTest = namedtuple(
    "InsertTest",
    (
        "input_data",
        "cmd_args",
        "table_exists",
        "expected_output",
        "should_error",
        "expected_table_json",
    ),
)


def make_format_test(content, arg):
    return InsertTest(
        input_data=content,
        # Using --silent to force no display of progress bar, since it won't
        # be shown for the JSON formats anyway
        cmd_args=["--silent", "--create"] + ([arg] if arg is not None else []),
        table_exists=False,
        expected_output="",
        should_error=False,
        expected_table_json=[{"rowid": 1, "a": 1, "b": 2, "c": 3}],
    )


@pytest.mark.parametrize(
    "input_data,cmd_args,table_exists,expected_output,should_error,expected_table_json",
    (
        # Auto-detect formats
        make_format_test(SIMPLE_CSV, None),
        make_format_test(SIMPLE_TSV, None),
        make_format_test(SIMPLE_JSON, None),
        make_format_test(SIMPLE_JSON_NL, None),
        # Explicit formats
        make_format_test(SIMPLE_CSV, "--csv"),
        make_format_test(SIMPLE_TSV, "--tsv"),
        make_format_test(SIMPLE_JSON, "--json"),
        make_format_test(SIMPLE_JSON_NL, "--nl"),
        # No --create option should error:
        InsertTest(
            input_data=SIMPLE_CSV,
            cmd_args=[],
            table_exists=False,
            expected_output="Inserting rows\nError: Table not found: table1\n",
            should_error=True,
            expected_table_json=None,
        ),
        # --no-detect-types
        InsertTest(
            input_data=SIMPLE_CSV,
            cmd_args=["--no-detect-types", "--create"],
            table_exists=False,
            expected_output="Inserting rows\n",
            should_error=False,
            expected_table_json=[{"rowid": 1, "a": "1", "b": "2", "c": "3"}],
        ),
        # --encoding - without it this should error:
        InsertTest(
            input_data=LATIN1_CSV,
            cmd_args=["--no-detect-types", "--create", "--csv"],
            table_exists=False,
            expected_output="Inserting rows\n",
            should_error=True,
            expected_table_json=None,
        ),
        # --encoding - with it this should work:
        InsertTest(
            input_data=LATIN1_CSV,
            cmd_args=[
                "--no-detect-types",
                "--create",
                "--encoding",
                "latin-1",
                "--csv",
            ],
            table_exists=False,
            expected_output="Inserting rows\n",
            should_error=False,
            expected_table_json=[
                {
                    "rowid": 1,
                    "date": "2020-01-01",
                    "name": "Barra da Lagoa",
                    "latitude": "-27.574",
                    "longitude": "-48.422",
                },
                {
                    "rowid": 2,
                    "date": "2020-03-04",
                    "name": "São Paulo",
                    "latitude": "-23.561",
                    "longitude": "-46.645",
                },
                {
                    "rowid": 3,
                    "date": "2020-04-05",
                    "name": "Salta",
                    "latitude": "-24.793:-65.408",
                    "longitude": None,
                },
            ],
        ),
        # Existing table, conflicting pk
        InsertTest(
            input_data=SIMPLE_CSV,
            cmd_args=[],
            table_exists=True,
            expected_output="Inserting rows\nUNIQUE constraint failed: table1.a\nError: UNIQUE constraint failed: table1.a\n",
            should_error=True,
            expected_table_json=[{"a": 1, "b": 2, "c": 3}, {"a": 4, "b": 5, "c": 6}],
        ),
        # Existing table, --replace
        InsertTest(
            input_data="a,b,c\n1,2,4\n",
            cmd_args=["--replace"],
            table_exists=True,
            expected_output="Inserting rows\n",
            should_error=False,
            expected_table_json=[{"a": 1, "b": 2, "c": 4}, {"a": 4, "b": 5, "c": 6}],
        ),
        # Existing table, --ignore
        InsertTest(
            input_data="a,b,c\n1,2,4\n",
            cmd_args=["--ignore"],
            table_exists=True,
            expected_output="Inserting rows\n",
            should_error=False,
            expected_table_json=[{"a": 1, "b": 2, "c": 3}, {"a": 4, "b": 5, "c": 6}],
        ),
    ),
)
def test_insert_against_datasette(
    httpx_mock,
    tmpdir,
    input_data,
    cmd_args,
    table_exists,
    expected_output,
    should_error,
    expected_table_json,
):
    ds = Datasette(
        config={
            "permissions": {
                "create-table": {"id": "*"},
                "insert-row": {"id": "*"},
                "update-row": {"id": "*"},
            }
        }
    )
    db = ds.add_memory_database("data")
    loop = asyncio.get_event_loop()

    # Drop all tables in the database each time, because in-memory
    # databases persist in between test runs
    drop_all_tables(db, loop)

    if table_exists:

        async def run_table_exists():
            await db.execute_write(
                "create table table1 (a integer primary key, b integer, c integer)"
            )
            await db.execute_write(
                "insert into table1 (a, b, c) values (1, 2, 3), (4, 5, 6)"
            )

        loop.run_until_complete(run_table_exists())

    token = ds.create_token("actor")

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

    path = pathlib.Path(tmpdir) / "data.txt"
    if isinstance(input_data, str):
        path.write_text(input_data)
    else:
        path.write_bytes(input_data)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "insert",
            "http://datasette.example.com/data",
            "table1",
            str(path),
            "--token",
            token,
        ]
        + cmd_args,
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


def drop_all_tables(db, loop):
    async def run():
        for table in await db.table_names():
            await db.execute_write("drop table {}".format(table))

    loop.run_until_complete(run())
