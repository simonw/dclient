import click
import httpx
import itertools
import json
import pathlib
from sqlite_utils.utils import rows_from_file, Format, TypeTracker
from .utils import token_for_url

INSERT_BATCH_SIZE = 100


def get_config_dir():
    return pathlib.Path(click.get_app_dir("io.datasette.dclient"))


@click.group()
@click.version_option()
def cli():
    "A client CLI utility for Datasette instances"


@cli.command()
@click.argument("url_or_alias")
@click.argument("sql")
@click.option("--token", "-t", help="API token")
def query(url_or_alias, sql, token):
    """
    Run a SQL query against a Datasette database URL

    Returns a JSON array of objects
    """
    aliases_file = get_config_dir() / "aliases.json"
    aliases = _load_aliases(aliases_file)
    if url_or_alias in aliases:
        url = aliases[url_or_alias]
    else:
        url = url_or_alias
    if not url_or_alias.endswith(".json"):
        url += ".json"
    if token is None:
        # Maybe there's a token in auth.json?
        token = token_for_url(url, _load_auths(get_config_dir() / "auth.json"))
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = httpx.get(url, params={"sql": sql, "_shape": "objects"}, headers=headers)
    if response.status_code != 200:
        # Is it valid JSON?
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise click.ClickException(
                "{} status code. Response was not valid JSON".format(
                    response.status_code
                )
            )
        bits = []
        if data.get("title"):
            bits.append(data["title"])
        if data.get("error"):
            bits.append(data["error"])
        raise click.ClickException(
            "{} status code. {}".format(response.status_code, ": ".join(bits))
        )

    # We should have JSON now
    try:
        data = response.json()
    except json.JSONDecodeError:
        raise click.ClickException("Response was not valid JSON")
    # ... but it may have a {"ok": false} error
    if not data.get("ok"):
        bits = []
        if data.get("title"):
            bits.append(data["title"])
        if data.get("error"):
            bits.append(data["error"])
        if not bits:
            bits = [json.dumps(data)]
        raise click.ClickException(": ".join(bits))

    # Output results
    click.echo(json.dumps(response.json()["rows"], indent=2))


@cli.command()
@click.argument("url_or_alias")
@click.argument("table")
@click.argument("file", type=click.File("rb"))
@click.option("format_csv", "--csv", is_flag=True, help="Input is CSV")
@click.option("format_tsv", "--tsv", is_flag=True, help="Input is TSV")
@click.option("format_json", "--json", is_flag=True, help="Input is JSON")
@click.option("format_nl", "--nl", is_flag=True, help="Input is newline-delimited JSON")
@click.option(
    "--no-detect-types", is_flag=True, help="Don't detect column types for CSV/TSV"
)
@click.option("--create", is_flag=True, help="Create table if it does not exist")
@click.option("--token", "-t", help="API token")
def insert(
    url_or_alias,
    table,
    file,
    format_csv,
    format_tsv,
    format_json,
    format_nl,
    no_detect_types,
    create,
    token,
):
    """
    Insert data into a remote Datasette instance

    Example usage:

    \b
        dclient insert \\
          https://private.datasette.cloud/data \\
          mytable data.csv
    """
    aliases_file = get_config_dir() / "aliases.json"
    aliases = _load_aliases(aliases_file)
    if url_or_alias in aliases:
        url = aliases[url_or_alias]
    else:
        url = url_or_alias

    if token is None:
        token = token_for_url(url, _load_auths(get_config_dir() / "auth.json"))

    print(url, table)
    format = None
    if format_csv:
        format = Format.CSV
    elif format_tsv:
        format = Format.CSV
    elif format_json:
        format = Format.JSON
    elif format_nl:
        format = Format.NL
    if format is None and file.name == "<stdin>":
        raise click.ClickException(
            "An explicit format is required  - e.g. --csv "
            "- when reading from standard input"
        )
    rows, format = rows_from_file(file, format=format)

    first = True

    for batch in _batches(rows, INSERT_BATCH_SIZE):
        types = None
        if first and not no_detect_types:
            # Detect types on first batch
            tracker = TypeTracker()
            list(tracker.wrap(batch))
            types = tracker.types
            # Convert types
            for row in batch:
                for key, value in row.items():
                    if value is None:
                        continue
                    if types[key] == "integer":
                        if not value:
                            row[key] = None
                        else:
                            row[key] = int(value)
                    elif types[key] == "float":
                        if not value:
                            row[key] = None
                        else:
                            row[key] = float(value)
        first = False
        response = _insert_batch(url, table, batch, token=token, create=create)
        print(response)


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


@alias.command(name="add")
@click.argument("name")
@click.argument("url")
def alias_add(name, url):
    "Add an alias"
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    aliases_file = config_dir / "aliases.json"
    aliases = _load_aliases(aliases_file)
    aliases[name] = url
    aliases_file.write_text(json.dumps(aliases, indent=4))


@alias.command(name="remove")
@click.argument("name")
def alias_remove(name):
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


@auth.command(name="add")
@click.argument("alias_or_url")
@click.option("--token", prompt=True, hide_input=True)
def auth_add(alias_or_url, token):
    """
    Add an authentication token for an alias or URL

    Example usage:

    \b
        dclient auth add https://datasette.io/content

    Paste in the token when prompted.
    """
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
def auth_list():
    "List stored API tokens"
    auths_file = get_config_dir() / "auth.json"
    click.echo("Tokens file: {}".format(auths_file))
    auths = _load_auths(auths_file)
    if auths:
        click.echo()
    for url, token in auths.items():
        click.echo("{}:\t{}..".format(url, token[:1]))


@auth.command(name="remove")
@click.argument("alias_or_url")
def auth_remove(alias_or_url):
    "Remove the API token for an alias or URL"
    config_dir = get_config_dir()
    auth_file = config_dir / "auth.json"
    auths = _load_auths(auth_file)
    try:
        del auths[alias_or_url]
        auth_file.write_text(json.dumps(auths, indent=4))
    except KeyError:
        raise click.ClickException("No such URL or alias")


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


def _batches(iterable, size):
    while True:
        batch = list(itertools.islice(iterable, size))
        if not batch:
            return
        yield batch


def _insert_batch(url, table, batch, token, create):
    if create:
        data = {
            "table": table,
            "rows": batch,
        }
        url = "{}/-/create".format(url)
    else:
        data = {
            "rows": batch,
        }
        url = "{}/{}/-/insert".format(url, table)
    response = httpx.post(
        url,
        headers={
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        },
        json=data,
        timeout=40.0,
    )
    response.raise_for_status()
    return response.json()
