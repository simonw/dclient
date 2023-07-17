import click
import httpx
import json
import pathlib


def get_config_dir():
    return pathlib.Path(click.get_app_dir("io.datasette.dclient"))


@click.group()
@click.version_option()
def cli():
    "A client CLI utility for Datasette instances"


@cli.command()
@click.argument("url")
@click.argument("sql")
@click.option("--token", "-t", help="API token")
def query(url, sql, token):
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
    if token is None:
        # Maybe there's a token in auth.json?
        token = _token_for_url_from_auth(url, get_config_dir() / "auth.json")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = httpx.get(url, params={"sql": sql, "_shape": "objects"}, headers=headers)
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


def _token_for_url_from_auth(url, auth_file):
    auths = _load_auths(auth_file)
    for auth_url, token in auths.items():
        if url.startswith(auth_url):
            return token


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


@cli.group()
def auth():
    "Manage authentication for different instances"


@auth.command()
@click.argument("alias_or_url")
@click.option("--token", prompt=True, hide_input=True)
def add(alias_or_url, token):
    "Add an authentication token"
    aliases_file = get_config_dir() / "aliases.json"
    aliases = _load_aliases(aliases_file)
    url = alias_or_url
    if alias_or_url in aliases:
        url = aliases[alias_or_url]
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    auth_file = config_dir / "auth.json"
    auths = _load_auths(auth_file)
    auths[url] = token
    auth_file.write_text(json.dumps(auths, indent=4))


@auth.command(name="list")
def list_():
    "List auths"
    auths_file = get_config_dir() / "auth.json"
    print(auths_file)
    auths = _load_auths(auths_file)
    click.echo(json.dumps(auths, indent=2))


def _load_aliases(aliases_file):
    if aliases_file.exists():
        aliases = json.loads(aliases_file.read_text())
    else:
        aliases = {}
    return aliases


def _load_auths(auth_file):
    if auth_file.exists():
        auths = json.loads(auth_file.read_text())
    else:
        auths = {}
    return auths
