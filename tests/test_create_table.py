"""Tests for the create-table command."""

from click.testing import CliRunner
from dclient.cli import cli
import json
import pathlib


def test_create_table_basic(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={
            "ok": True,
            "database": "mydb",
            "table": "dogs",
            "table_url": "http://example.com/mydb/dogs",
            "table_api_url": "http://example.com/mydb/dogs.json",
            "schema": "CREATE TABLE [dogs] (\n   [id] INTEGER PRIMARY KEY,\n   [name] TEXT\n)",
        },
        status_code=201,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create-table",
            "mydb",
            "dogs",
            "--column",
            "id",
            "integer",
            "--column",
            "name",
            "text",
            "--pk",
            "id",
            "-i",
            "https://example.com",
            "--token",
            "tok",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["table"] == "dogs"

    # Verify request
    request = httpx_mock.get_request()
    assert request.url.path == "/mydb/-/create"
    assert request.headers["authorization"] == "Bearer tok"
    body = json.loads(request.read())
    assert body["table"] == "dogs"
    assert body["columns"] == [
        {"name": "id", "type": "integer"},
        {"name": "name", "type": "text"},
    ]
    assert body["pk"] == "id"


def test_create_table_compound_pk(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(json={"ok": True}, status_code=201)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create-table",
            "mydb",
            "events",
            "--column",
            "user_id",
            "integer",
            "-c",
            "event_id",
            "integer",
            "--column",
            "data",
            "text",
            "--pk",
            "user_id",
            "--pk",
            "event_id",
            "-i",
            "https://example.com",
            "--token",
            "tok",
        ],
    )
    assert result.exit_code == 0, result.output
    body = json.loads(httpx_mock.get_request().read())
    assert body["pks"] == ["user_id", "event_id"]
    assert "pk" not in body


def test_create_table_no_pk(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(json={"ok": True}, status_code=201)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create-table",
            "mydb",
            "logs",
            "--column",
            "message",
            "text",
            "--column",
            "level",
            "integer",
            "-i",
            "https://example.com",
            "--token",
            "tok",
        ],
    )
    assert result.exit_code == 0, result.output
    body = json.loads(httpx_mock.get_request().read())
    assert "pk" not in body
    assert "pks" not in body


def test_create_table_no_columns_error(mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create-table",
            "mydb",
            "empty",
            "-i",
            "https://example.com",
            "--token",
            "tok",
        ],
    )
    assert result.exit_code == 1
    assert "at least one --column" in result.output


def test_create_table_api_error(httpx_mock, mocker, tmpdir):
    mocker.patch("dclient.cli.get_config_dir", return_value=pathlib.Path(tmpdir))
    httpx_mock.add_response(
        json={"ok": False, "errors": ["Table already exists: dogs"]},
        status_code=400,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create-table",
            "mydb",
            "dogs",
            "--column",
            "id",
            "integer",
            "-i",
            "https://example.com",
            "--token",
            "tok",
        ],
    )
    assert result.exit_code == 1
    assert "Table already exists" in result.output


def test_create_table_uses_default_instance(httpx_mock, mocker, tmpdir):
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
    httpx_mock.add_response(json={"ok": True}, status_code=201)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "create-table",
            "mydb",
            "t1",
            "--column",
            "id",
            "integer",
            "--token",
            "tok",
        ],
    )
    assert result.exit_code == 0, result.output
    request = httpx_mock.get_request()
    assert request.url.host == "prod.example.com"
    assert request.url.path == "/mydb/-/create"
