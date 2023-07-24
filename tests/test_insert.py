from click.testing import CliRunner
from dclient.cli import cli
import json
import pathlib


def test_insert_mocked(httpx_mock, tmpdir):
    httpx_mock.add_response(
        json={
            "ok": True,
            "database": "data",
            "table": "table1",
            "table_url": "http://localhost:8012/data/table1",
            "table_api_url": "http://localhost:8012/data/table1.json",
            "schema": "CREATE TABLE [table1] (...)",
            "row_count": 100,
        }
    )
    (tmpdir / "data.csv")
    path = pathlib.Path(tmpdir) / "data.csv"
    path.write_text("a,b,c\n1,2,3\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "insert",
            "https://localhost:8012/data",
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
