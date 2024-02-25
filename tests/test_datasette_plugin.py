from click.testing import CliRunner
from datasette.app import Datasette
from datasette.cli import cli
import pytest


def test_plugin_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["dc", "--help"])
    assert result.exit_code == 0
    assert "Usage: cli dc" in result.output
    bits = result.output.split("Commands:")
    assert "alias" in bits[1]
    assert "query" in bits[1]


@pytest.mark.asyncio
async def test_plugin_installed():
    ds = Datasette(memory=True)
    await ds.invoke_startup()
    response = await ds.client.get("/-/plugins.json")
    assert response.status_code == 200
    assert any(p["name"] == "dclient" for p in response.json())
