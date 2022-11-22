import click
import httpx
import json
import appdirs
import pathlib


def get_config_dir():
    return pathlib.Path(appdirs.user_config_dir("dclient"))


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
    aliases_file = get_config_dir() / "aliases.json"
    aliases = _load_aliases(aliases_file)
    if url in aliases:
        url = aliases[url]
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


@cli.group()
def alias():
    "Manage aliases for different instances"


@alias.command(name="list")
@click.option("_json", "--json", is_flag=True, help="Output raw JSON")
def list_(_json):
    "List aliases"
    aliases_file = get_config_dir() / "aliases.json"
    aliases = _load_aliases(aliases_file)
    if _json:
        click.echo(json.dumps(aliases, indent=2))
    else:
        for alias, url in aliases.items():
            click.echo(f"{alias} = {url}")


@alias.command()
@click.argument("name")
@click.argument("url")
def add(name, url):
    "Add an alias"
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    aliases_file = config_dir / "aliases.json"
    aliases = _load_aliases(aliases_file)
    aliases[name] = url
    aliases_file.write_text(json.dumps(aliases, indent=4))


@alias.command()
@click.argument("name")
def remove(name):
    "Remove an alias"
    config_dir = get_config_dir()
    aliases_file = config_dir / "aliases.json"
    aliases = _load_aliases(aliases_file)
    if name in aliases:
        del aliases[name]
        aliases_file.write_text(json.dumps(aliases, indent=4))
    else:
        raise click.ClickException("No such alias")


def _load_aliases(aliases_file):
    if aliases_file.exists():
        aliases = json.loads(aliases_file.read_text())
    else:
        aliases = {}
    return aliases
