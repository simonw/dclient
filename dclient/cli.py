import click
from click_default_group import DefaultGroup
import httpx
import json
import os
import pathlib
from sqlite_utils.utils import rows_from_file, Format, TypeTracker, progressbar
import sys
import textwrap
import time
from .utils import token_for_url
import urllib


def get_config_dir():
    env = os.environ.get("DCLIENT_CONFIG_DIR")
    if env:
        return pathlib.Path(env)
    return pathlib.Path(click.get_app_dir("io.datasette.dclient"))


def _load_config(config_file):
    if config_file.exists():
        return json.loads(config_file.read_text())
    return {"default_instance": None, "instances": {}}


def _save_config(config_file, config):
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps(config, indent=4))


def _load_auths(auth_file):
    if auth_file.exists():
        auths = json.loads(auth_file.read_text())
    else:
        auths = {}
    return auths


def _resolve_instance(instance, config_file):
    """Resolve instance: -i flag (alias or URL) → config default → DATASETTE_URL → error."""
    config = _load_config(config_file)
    if instance:
        # If it looks like a URL, use directly
        if instance.startswith("http://") or instance.startswith("https://"):
            return instance
        # Otherwise look up as alias
        if instance in config.get("instances", {}):
            return config["instances"][instance]["url"]
        raise click.ClickException(
            f"Unknown instance: {instance}. Use a URL or configure an alias."
        )
    # Try config default
    default = config.get("default_instance")
    if default and default in config.get("instances", {}):
        return config["instances"][default]["url"]
    # Try env var
    env_url = os.environ.get("DATASETTE_URL")
    if env_url:
        return env_url.rstrip("/")
    raise click.ClickException(
        "No instance specified. Use -i, set a default instance, or set DATASETTE_URL."
    )


def _resolve_database(database, instance_alias, config_file):
    """Resolve database: -d flag → instance default_database → DATASETTE_DATABASE → error."""
    if database:
        return database
    # Try instance's default_database from config
    if instance_alias:
        config = _load_config(config_file)
        instances = config.get("instances", {})
        if instance_alias in instances:
            default_db = instances[instance_alias].get("default_database")
            if default_db:
                return default_db
    # Try env var
    env_db = os.environ.get("DATASETTE_DATABASE")
    if env_db:
        return env_db
    raise click.ClickException(
        "No database specified. Use -d, set a default database, or set DATASETTE_DATABASE."
    )


def _instance_alias_for_url(url, config_file):
    """Find the alias name for a given instance URL, if any."""
    config = _load_config(config_file)
    for name, inst in config.get("instances", {}).items():
        if inst.get("url", "").rstrip("/") == url.rstrip("/"):
            return name
    return None


def _resolve_token(token, url, auth_file, config_file):
    """Resolve token: --token flag → auth.json by alias → auth.json by URL → DATASETTE_TOKEN → None."""
    if token is not None:
        return token
    auths = _load_auths(auth_file)
    # Try alias-based lookup
    alias = _instance_alias_for_url(url, config_file)
    if alias and alias in auths:
        return auths[alias]
    # Try URL-based prefix matching (fallback)
    stored = token_for_url(url, auths)
    if stored is not None:
        return stored
    return os.environ.get("DATASETTE_TOKEN")


@click.group(cls=DefaultGroup, default="default_query", default_if_no_args=False)
@click.version_option()
def cli():
    "A client CLI utility for Datasette instances"


def _make_request(url, token, extra_path="", params=None):
    """Make an authenticated GET request to a Datasette instance."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    full_url = url.rstrip("/") + extra_path
    response = httpx.get(
        full_url,
        headers=headers,
        params=params,
        follow_redirects=True,
        timeout=30.0,
    )
    return response


@cli.command()
@click.argument("path")
@click.option("-i", "--instance", default=None, help="Datasette instance URL or alias")
@click.option("--token", help="API token")
def get(path, instance, token):
    """
    Make an authenticated GET request to a Datasette instance

    Example usage:

    \b
        dclient get /-/plugins.json
        dclient get /data/creatures.json -i https://my.datasette.io
    """
    config_dir = get_config_dir()
    url = _resolve_instance(instance, config_dir / "config.json")
    token = _resolve_token(token, url, config_dir / "auth.json", config_dir / "config.json")
    full_url = url.rstrip("/") + "/" + path.lstrip("/")
    response = _make_request(url, token, "/" + path.lstrip("/"))
    if response.status_code != 200:
        raise click.ClickException(f"{response.status_code} error for {full_url}")
    if "json" in response.headers.get("content-type", ""):
        click.echo(json.dumps(response.json(), indent=2))
    else:
        click.echo(response.text)


@cli.command()
@click.option("-i", "--instance", default=None, help="Datasette instance URL or alias")
@click.option("--json", "_json", is_flag=True, help="Output raw JSON")
@click.option("--token", help="API token")
def databases(instance, _json, token):
    """
    List databases on an instance

    Example usage:

    \b
        dclient databases
        dclient databases -i https://latest.datasette.io
    """
    config_dir = get_config_dir()
    url = _resolve_instance(instance, config_dir / "config.json")
    token = _resolve_token(token, url, config_dir / "auth.json", config_dir / "config.json")
    response = _make_request(url, token, "/.json")
    if response.status_code != 200:
        raise click.ClickException(f"{response.status_code} error")
    data = response.json()
    databases_data = data.get("databases", data if isinstance(data, list) else {})
    # Normalize: could be a dict {name: info} or a list [{name: ...}, ...]
    if isinstance(databases_data, dict):
        db_list = list(databases_data.values())
    else:
        db_list = databases_data
    if _json:
        click.echo(json.dumps(db_list, indent=2))
    else:
        for db in db_list:
            name = db["name"] if isinstance(db, dict) else db
            click.echo(name)


@cli.command()
@click.option("-i", "--instance", default=None, help="Datasette instance URL or alias")
@click.option("-d", "--database", default=None, help="Database name")
@click.option("--views", is_flag=True, help="Include views")
@click.option("--views-only", is_flag=True, help="Only show views")
@click.option("--hidden", is_flag=True, help="Include hidden tables")
@click.option("--json", "_json", is_flag=True, help="Output raw JSON")
@click.option("--token", help="API token")
def tables(instance, database, views, views_only, hidden, _json, token):
    """
    List tables in a database

    Example usage:

    \b
        dclient tables
        dclient tables -d fixtures -i https://latest.datasette.io
    """
    config_dir = get_config_dir()
    url = _resolve_instance(instance, config_dir / "config.json")
    instance_alias = _instance_alias_for_url(url, config_dir / "config.json") if not (instance and (instance.startswith("http://") or instance.startswith("https://"))) else None
    if instance and not (instance.startswith("http://") or instance.startswith("https://")):
        instance_alias = instance
    token = _resolve_token(token, url, config_dir / "auth.json", config_dir / "config.json")
    db = _resolve_database(database, instance_alias, config_dir / "config.json")
    response = _make_request(url, token, f"/{db}.json")
    if response.status_code != 200:
        raise click.ClickException(f"{response.status_code} error")
    data = response.json()
    table_list = data.get("tables", [])
    view_list = data.get("views", [])
    if _json:
        if views_only:
            click.echo(json.dumps(view_list, indent=2))
        elif views:
            click.echo(json.dumps(table_list + view_list, indent=2))
        else:
            click.echo(json.dumps(table_list, indent=2))
    else:
        items = []
        if not views_only:
            for t in table_list:
                if not hidden and t.get("hidden"):
                    continue
                name = t["name"] if isinstance(t, dict) else t
                count = t.get("count") if isinstance(t, dict) else None
                if count is not None:
                    items.append(f"{name}\t{count} rows")
                else:
                    items.append(name)
        if views or views_only:
            for v in view_list:
                name = v["name"] if isinstance(v, dict) else v
                items.append(name)
        for item in items:
            click.echo(item)


@cli.command()
@click.argument("database")
@click.argument("sql")
@click.option("-i", "--instance", default=None, help="Datasette instance URL or alias")
@click.option("--token", help="API token")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output: show HTTP request")
def query(database, sql, instance, token, verbose):
    """
    Run a SQL query against a Datasette database

    Requires both a database name and a SQL string.

    Example usage:

    \b
        dclient query fixtures "select * from facetable limit 5"
        dclient query analytics "select count(*) from events" -i staging
    """
    config_dir = get_config_dir()
    url = _resolve_instance(instance, config_dir / "config.json")
    token = _resolve_token(token, url, config_dir / "auth.json", config_dir / "config.json")
    query_url = url.rstrip("/") + "/" + database + ".json"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    params = {"sql": sql, "_shape": "objects"}
    if verbose:
        click.echo(query_url + "?" + urllib.parse.urlencode(params), err=True)
    response = httpx.get(query_url, params=params, headers=headers, follow_redirects=True)

    if response.status_code != 200:
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

    try:
        data = response.json()
    except json.JSONDecodeError:
        raise click.ClickException("Response was not valid JSON")
    if not data.get("ok"):
        bits = []
        if data.get("title"):
            bits.append(data["title"])
        if data.get("error"):
            bits.append(data["error"])
        if not bits:
            bits = [json.dumps(data)]
        raise click.ClickException(": ".join(bits))

    click.echo(json.dumps(response.json()["rows"], indent=2))


def _do_insert(database, table, filepath, format_csv, format_tsv, format_json,
               format_nl, encoding, no_detect_types, replace, ignore, create,
               alter, pks, batch_size, interval, token, silent, verbose,
               instance, endpoint="insert"):
    """Shared implementation for insert and upsert commands."""
    config_dir = get_config_dir()
    url = _resolve_instance(instance, config_dir / "config.json")
    token = _resolve_token(token, url, config_dir / "auth.json", config_dir / "config.json")

    format = None
    if format_csv:
        format = Format.CSV
    elif format_tsv:
        format = Format.TSV
    elif format_json:
        format = Format.JSON
    elif format_nl:
        format = Format.NL
    if format is None and filepath == "-":
        raise click.ClickException(
            "An explicit format is required  - e.g. --csv "
            "- when reading from standard input"
        )

    if filepath != "-":
        file_size = pathlib.Path(filepath).stat().st_size
        fp = open(filepath, "rb")
    else:
        fp = sys.stdin.buffer
        file_size = None

    try:
        rows, format = rows_from_file(fp, format=format, encoding=encoding)
    except Exception as ex:
        raise click.ClickException(str(ex))

    if format in (Format.JSON, Format.NL):
        file_size = None
        no_detect_types = True

    first = True
    base_url = url.rstrip("/") + "/" + database

    with progressbar(
        length=file_size,
        label="Inserting rows",
        silent=silent or (file_size is None),
        show_percent=True,
    ) as bar:
        bytes_so_far = 0
        for batch in _batches(rows, batch_size, interval=interval):
            if file_size is not None:
                try:
                    bytes_consumed_so_far = fp.tell()
                    new_bytes = bytes_consumed_so_far - bytes_so_far
                    bar.update(new_bytes)
                    bytes_so_far += new_bytes
                except ValueError:
                    pass
            types = None
            if first and not no_detect_types:
                tracker = TypeTracker()
                list(tracker.wrap(batch))
                types = tracker.types
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
            _insert_batch(
                url=base_url,
                table=table,
                batch=batch,
                token=token,
                create=create,
                alter=alter,
                pks=pks,
                replace=replace,
                ignore=ignore,
                verbose=verbose,
                endpoint=endpoint,
            )


_insert_options = [
    click.argument("database"),
    click.argument("table"),
    click.argument(
        "filepath", type=click.Path("rb", readable=True, allow_dash=True, dir_okay=False)
    ),
    click.option("-i", "--instance", default=None, help="Datasette instance URL or alias"),
    click.option("format_csv", "--csv", is_flag=True, help="Input is CSV"),
    click.option("format_tsv", "--tsv", is_flag=True, help="Input is TSV"),
    click.option("format_json", "--json", is_flag=True, help="Input is JSON"),
    click.option("format_nl", "--nl", is_flag=True, help="Input is newline-delimited JSON"),
    click.option("--encoding", help="Character encoding for CSV/TSV"),
    click.option(
        "--no-detect-types", is_flag=True, help="Don't detect column types for CSV/TSV"
    ),
    click.option("--alter", is_flag=True, help="Alter table to add any missing columns"),
    click.option(
        "pks", "--pk", multiple=True,
        help="Columns to use as the primary key when creating the table",
    ),
    click.option(
        "--batch-size", type=int, default=100, help="Send rows in batches of this size"
    ),
    click.option(
        "--interval", type=float, default=10, help="Send batch at least every X seconds"
    ),
    click.option("--token", "-t", help="API token"),
    click.option("--silent", is_flag=True, help="Don't output progress"),
    click.option(
        "-v", "--verbose", is_flag=True,
        help="Verbose output: show HTTP request and response",
    ),
]


def _apply_options(options):
    def decorator(func):
        for option in reversed(options):
            func = option(func)
        return func
    return decorator


@cli.command()
@_apply_options(_insert_options)
@click.option("--replace", is_flag=True, help="Replace rows with a matching primary key")
@click.option("--ignore", is_flag=True, help="Ignore rows with a matching primary key")
@click.option("--create", is_flag=True, help="Create table if it does not exist")
def insert(database, table, filepath, instance, format_csv, format_tsv, format_json,
           format_nl, encoding, no_detect_types, alter, pks, batch_size, interval,
           token, silent, verbose, replace, ignore, create):
    """
    Insert data into a remote Datasette instance

    Example usage:

    \b
        dclient insert main mytable data.csv --csv -i myapp
        dclient insert main mytable data.csv --csv --create --pk id
    """
    _do_insert(database, table, filepath, format_csv, format_tsv, format_json,
               format_nl, encoding, no_detect_types, replace, ignore, create,
               alter, pks, batch_size, interval, token, silent, verbose,
               instance, endpoint="insert")


@cli.command()
@_apply_options(_insert_options)
def upsert(database, table, filepath, instance, format_csv, format_tsv, format_json,
           format_nl, encoding, no_detect_types, alter, pks, batch_size, interval,
           token, silent, verbose):
    """
    Upsert data into a remote Datasette instance

    Example usage:

    \b
        dclient upsert main mytable data.csv --csv -i myapp
    """
    _do_insert(database, table, filepath, format_csv, format_tsv, format_json,
               format_nl, encoding, no_detect_types, False, False, False,
               alter, pks, batch_size, interval, token, silent, verbose,
               instance, endpoint="upsert")


@cli.command()
@click.argument("table_name", required=False, default=None)
@click.option("-i", "--instance", default=None, help="Datasette instance URL or alias")
@click.option("-d", "--database", default=None, help="Database name")
@click.option("--json", "_json", is_flag=True, help="Output raw JSON")
@click.option("--token", help="API token")
def schema(table_name, instance, database, _json, token):
    """
    Show SQL schema for a database or specific table

    Example usage:

    \b
        dclient schema
        dclient schema facetable
        dclient schema -d analytics
    """
    config_dir = get_config_dir()
    url = _resolve_instance(instance, config_dir / "config.json")
    instance_alias = _instance_alias_for_url(url, config_dir / "config.json") if not (instance and (instance.startswith("http://") or instance.startswith("https://"))) else None
    if instance and not (instance.startswith("http://") or instance.startswith("https://")):
        instance_alias = instance
    token = _resolve_token(token, url, config_dir / "auth.json", config_dir / "config.json")
    db = _resolve_database(database, instance_alias, config_dir / "config.json")
    if table_name:
        response = _make_request(url, token, f"/{db}/{table_name}/-/schema.json")
    else:
        response = _make_request(url, token, f"/{db}/-/schema.json")
    if response.status_code != 200:
        raise click.ClickException(f"{response.status_code} error")
    data = response.json()
    if _json:
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo(data.get("schema", ""))


@cli.command()
@click.option("-i", "--instance", default=None, help="Datasette instance URL or alias")
@click.option("--json", "_json", is_flag=True, help="Output raw JSON")
@click.option("--token", help="API token")
def plugins(instance, _json, token):
    """
    List installed plugins on an instance

    Example usage:

    \b
        dclient plugins
        dclient plugins -i https://latest.datasette.io
    """
    config_dir = get_config_dir()
    url = _resolve_instance(instance, config_dir / "config.json")
    token = _resolve_token(token, url, config_dir / "auth.json", config_dir / "config.json")
    response = _make_request(url, token, "/-/plugins.json")
    if response.status_code != 200:
        raise click.ClickException(f"{response.status_code} error")
    data = response.json()
    if _json:
        click.echo(json.dumps(data, indent=2))
    else:
        for plugin in data:
            name = plugin["name"] if isinstance(plugin, dict) else plugin
            click.echo(name)


@cli.command()
@click.option("-i", "--instance", default=None, help="Datasette instance URL or alias")
@click.option("--token", help="API token")
def actor(instance, token):
    """
    Show the actor represented by an API token

    Example usage:

    \b
        dclient actor
        dclient actor -i prod
    """
    config_dir = get_config_dir()
    url = _resolve_instance(instance, config_dir / "config.json")
    token = _resolve_token(token, url, config_dir / "auth.json", config_dir / "config.json")
    response = _make_request(url, token, "/-/actor.json")
    response.raise_for_status()
    click.echo(json.dumps(response.json(), indent=4))


@cli.command(name="default_query", hidden=True)
@click.argument("sql")
@click.option("-i", "--instance", default=None, help="Datasette instance URL or alias")
@click.option("-d", "--database", default=None, help="Database name")
@click.option("--token", help="API token")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output: show HTTP request")
def default_query(sql, instance, database, token, verbose):
    """Run a SQL query using default instance and database."""
    config_dir = get_config_dir()
    url = _resolve_instance(instance, config_dir / "config.json")
    instance_alias = _instance_alias_for_url(url, config_dir / "config.json") if not (instance and (instance.startswith("http://") or instance.startswith("https://"))) else None
    if instance and not (instance.startswith("http://") or instance.startswith("https://")):
        instance_alias = instance
    token = _resolve_token(token, url, config_dir / "auth.json", config_dir / "config.json")
    db = _resolve_database(database, instance_alias, config_dir / "config.json")
    query_url = url.rstrip("/") + "/" + db + ".json"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    params = {"sql": sql, "_shape": "objects"}
    if verbose:
        click.echo(query_url + "?" + urllib.parse.urlencode(params), err=True)
    response = httpx.get(query_url, params=params, headers=headers, follow_redirects=True)

    if response.status_code != 200:
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

    try:
        data = response.json()
    except json.JSONDecodeError:
        raise click.ClickException("Response was not valid JSON")
    if not data.get("ok"):
        bits = []
        if data.get("title"):
            bits.append(data["title"])
        if data.get("error"):
            bits.append(data["error"])
        if not bits:
            bits = [json.dumps(data)]
        raise click.ClickException(": ".join(bits))

    click.echo(json.dumps(response.json()["rows"], indent=2))


# -- alias command group --


@cli.group()
def alias():
    "Manage aliases for different instances"


@alias.command(name="list")
@click.option("_json", "--json", is_flag=True, help="Output raw JSON")
def alias_list(_json):
    """List aliases"""
    config_file = get_config_dir() / "config.json"
    config = _load_config(config_file)
    instances = config.get("instances", {})
    default = config.get("default_instance")
    if _json:
        click.echo(json.dumps(config, indent=2))
    else:
        for name, inst in instances.items():
            marker = "* " if name == default else "  "
            db_info = f" (db: {inst['default_database']})" if inst.get("default_database") else ""
            click.echo(f"{marker}{name} = {inst['url']}{db_info}")


@alias.command(name="add")
@click.argument("name")
@click.argument("url")
def alias_add(name, url):
    """
    Add an alias for a Datasette instance

    Example usage:

    \b
        dclient alias add prod https://myapp.datasette.cloud
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"
    config = _load_config(config_file)
    config["instances"][name] = {"url": url, "default_database": None}
    _save_config(config_file, config)


@alias.command(name="remove")
@click.argument("name")
def alias_remove(name):
    """
    Remove an alias

    Example usage:

    \b
        dclient alias remove prod
    """
    config_file = get_config_dir() / "config.json"
    config = _load_config(config_file)
    if name in config.get("instances", {}):
        del config["instances"][name]
        if config.get("default_instance") == name:
            config["default_instance"] = None
        _save_config(config_file, config)
    else:
        raise click.ClickException("No such alias")


@alias.command(name="default")
@click.argument("name", required=False, default=None)
@click.option("--clear", is_flag=True, help="Clear default instance")
def alias_default(name, clear):
    """
    Set or show the default instance

    Example usage:

    \b
        dclient alias default prod
        dclient alias default
        dclient alias default --clear
    """
    config_file = get_config_dir() / "config.json"
    config = _load_config(config_file)
    if clear:
        config["default_instance"] = None
        _save_config(config_file, config)
    elif name:
        if name not in config.get("instances", {}):
            raise click.ClickException(f"No such alias: {name}")
        config["default_instance"] = name
        _save_config(config_file, config)
    else:
        default = config.get("default_instance")
        if default:
            click.echo(default)
        else:
            click.echo("No default instance set")


@alias.command(name="default-db")
@click.argument("alias_name")
@click.argument("db", required=False, default=None)
@click.option("--clear", is_flag=True, help="Clear default database for this alias")
def alias_default_db(alias_name, db, clear):
    """
    Set or show the default database for an alias

    Example usage:

    \b
        dclient alias default-db prod main
        dclient alias default-db prod
        dclient alias default-db prod --clear
    """
    config_file = get_config_dir() / "config.json"
    config = _load_config(config_file)
    if alias_name not in config.get("instances", {}):
        raise click.ClickException(f"No such alias: {alias_name}")
    if clear:
        config["instances"][alias_name]["default_database"] = None
        _save_config(config_file, config)
    elif db:
        config["instances"][alias_name]["default_database"] = db
        _save_config(config_file, config)
    else:
        default_db = config["instances"][alias_name].get("default_database")
        if default_db:
            click.echo(default_db)
        else:
            click.echo(f"No default database set for {alias_name}")


# -- auth command group --


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
        dclient auth add prod
        dclient auth add https://datasette.io

    Paste in the token when prompted.
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    auth_file = config_dir / "auth.json"
    auths = _load_auths(auth_file)
    # Store by alias name or URL as-is
    auths[alias_or_url] = token
    auth_file.write_text(json.dumps(auths, indent=4))


@auth.command(name="list")
def auth_list():
    """
    List stored API tokens

    Example usage:

    \b
        dclient auth list
    """
    auths_file = get_config_dir() / "auth.json"
    click.echo("Tokens file: {}".format(auths_file))
    auths = _load_auths(auths_file)
    if auths:
        click.echo()
    for key, token in auths.items():
        click.echo("{}:\t{}..".format(key, token[:1]))


@auth.command(name="remove")
@click.argument("alias_or_url")
def auth_remove(alias_or_url):
    """
    Remove the API token for an alias or URL

    Example usage:

    \b
        dclient auth remove prod
    """
    config_dir = get_config_dir()
    auth_file = config_dir / "auth.json"
    auths = _load_auths(auth_file)
    try:
        del auths[alias_or_url]
        auth_file.write_text(json.dumps(auths, indent=4))
    except KeyError:
        raise click.ClickException("No such URL or alias")


@auth.command(name="status")
@click.option("-i", "--instance", default=None, help="Datasette instance URL or alias")
@click.option("--token", help="API token")
def auth_status(instance, token):
    """
    Verify authentication by calling /-/actor.json

    Example usage:

    \b
        dclient auth status
        dclient auth status -i prod
    """
    config_dir = get_config_dir()
    url = _resolve_instance(instance, config_dir / "config.json")
    token = _resolve_token(token, url, config_dir / "auth.json", config_dir / "config.json")
    response = _make_request(url, token, "/-/actor.json")
    response.raise_for_status()
    click.echo(json.dumps(response.json(), indent=4))


# -- v1 → v2 migration --


def _migrate_v1_to_v2(config_dir):
    """Migrate v1 aliases.json + auth.json to v2 config.json + auth.json."""
    config_file = config_dir / "config.json"
    aliases_file = config_dir / "aliases.json"
    auth_file = config_dir / "auth.json"

    if config_file.exists() or not aliases_file.exists():
        return

    aliases = json.loads(aliases_file.read_text()) if aliases_file.exists() else {}
    old_auths = json.loads(auth_file.read_text()) if auth_file.exists() else {}

    config = {"default_instance": None, "instances": {}}
    new_auths = {}
    url_to_alias = {}

    for alias_name, alias_url in aliases.items():
        parsed = urllib.parse.urlparse(alias_url)
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) == 1:
            # URL has a single path segment → instance URL + default database
            instance_url = f"{parsed.scheme}://{parsed.netloc}"
            default_db = path_parts[0]
        else:
            instance_url = alias_url
            default_db = None
        config["instances"][alias_name] = {
            "url": instance_url,
            "default_database": default_db,
        }
        url_to_alias[alias_url] = alias_name

    # Migrate auth keys from URLs to alias names
    for url, token in old_auths.items():
        if url in url_to_alias:
            new_auths[url_to_alias[url]] = token
        else:
            # Keep URL-keyed entries as fallbacks
            new_auths[url] = token

    _save_config(config_file, config)
    if new_auths or old_auths:
        auth_file.rename(config_dir / "auth.json.bak")
        auth_file.write_text(json.dumps(new_auths, indent=4))
    aliases_file.rename(config_dir / "aliases.json.bak")



def _batches(iterable, size, interval=None):
    iterable = iter(iterable)
    last_yield_time = time.time()
    while True:
        batch = []
        for _ in range(size):
            try:
                batch.append(next(iterable))
            except StopIteration:
                break
            if interval is not None and time.time() - last_yield_time >= interval:
                break
        if not batch:
            return
        yield batch
        last_yield_time = time.time()


def _insert_batch(
    *, url, table, batch, token, create, alter, pks, replace, ignore, verbose,
    endpoint="insert"
):
    if create:
        data = {
            "table": table,
            "rows": batch,
        }
        if replace:
            data["replace"] = True
        if ignore:
            data["ignore"] = True
        if alter:
            data["alter"] = True
        if pks:
            if len(pks) == 1:
                data["pk"] = pks[0]
            else:
                data["pks"] = pks
        url = "{}/-/create".format(url)
    else:
        data = {
            "rows": batch,
        }
        if replace:
            data["replace"] = True
        if ignore:
            data["ignore"] = True
        if alter:
            data["alter"] = True
        url = "{}/{}/-/{}".format(url, table, endpoint)
    if verbose:
        click.echo("POST {}".format(url), err=True)
        click.echo(textwrap.indent(json.dumps(data, indent=2), "  "), err=True)
    response = httpx.post(
        url,
        headers={
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        },
        json=data,
        timeout=40.0,
    )
    if verbose:
        click.echo(str(response), err=True)
    if str(response.status_code)[0] != "2":
        # Is there an error we can show?
        if "/json" in response.headers["content-type"]:
            data = response.json()
            if "errors" in data:
                raise click.ClickException("\n".join(data["errors"]))
        response.raise_for_status()
    response_data = response.json()
    if verbose:
        click.echo(textwrap.indent(json.dumps(response_data, indent=2), "  "), err=True)
    return response_data
