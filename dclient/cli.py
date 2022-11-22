import click
import httpx
import json


@click.group()
@click.version_option()
def cli():
    "A client CLI utility for Datasette instances"


@cli.command()
@click.argument("url")
@click.argument("sql")
def query(url, sql):
    """
    Run a SQL query against a Datasette database URL

    Returns a JSON array of objects
    """
    if not url.endswith(".json"):
        url += ".json"
    response = httpx.get(url, params={"sql": sql, "_shape": "objects"})
    if response.status_code != 200 or not response.json()["ok"]:
        data = response.json()
        bits = []
        if data.get("title"):
            bits.append(data["title"])
        if data.get("error"):
            bits.append(data["error"])
        raise click.ClickException(": ".join(bits))
    else:
        click.echo(json.dumps(response.json()["rows"], indent=2))
