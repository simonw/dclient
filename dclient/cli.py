import click
from click_default_group import DefaultGroup
import csv
import httpx
import io
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
    if default:
        if default in config.get("instances", {}):
            return config["instances"][default]["url"]
        if default.startswith("http://") or default.startswith("https://"):
            return default.rstrip("/")
    # Try env var
    env_url = os.environ.get("DATASETTE_URL")
    if env_url:
        return env_url.rstrip("/")
    raise click.ClickException(
        "No instance specified. Use -i <url-or-alias>, or configure a default:\n\n"
        "    dclient alias add <name> <url>\n"
        "    dclient default instance <name-or-url>\n\n"
        "Or set the DATASETTE_URL environment variable."
    )


def _resolve_database(database, instance_alias, config_file):
    """Resolve database: -d flag → instance default_database → DATASETTE_DATABASE → error."""
    if database:
        return database
    # Try instance's default_database from config
    if instance_alias:
        config = _load_config(config_file)
        instances = config.get("instances", {})
        key = instance_alias
        if key not in instances and (
            key.startswith("http://") or key.startswith("https://")
        ):
            key = _instance_alias_for_url(key, config_file)
        if key in instances:
            default_db = instances[key].get("default_database")
            if default_db:
                return default_db
    # Try env var
    env_db = os.environ.get("DATASETTE_DATABASE")
    if env_db:
        return env_db
    raise click.ClickException(
        "No database specified. Use -d <name>, or configure a default:\n\n"
        "    dclient default database <alias-or-url> <database>\n\n"
        "Or set the DATASETTE_DATABASE environment variable."
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


def _output_rows(rows, fmt, columns=None):
    """Output rows in the specified format. fmt is one of 'json', 'csv', 'tsv', 'nl', 'table'."""
    if fmt == "csv":
        _output_csv(rows, columns)
    elif fmt == "tsv":
        _output_csv(rows, columns, delimiter="\t")
    elif fmt == "nl":
        for row in rows:
            click.echo(json.dumps(row, default=str))
    elif fmt == "table":
        _output_table(rows, columns)
    else:
        click.echo(json.dumps(rows, indent=2, default=str))


def _output_csv(rows, columns=None, delimiter=","):
    if not rows and not columns:
        return
    if columns is None:
        columns = list(rows[0].keys()) if rows else []
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=delimiter)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(str(row.get(col, "")) for col in columns)
    click.echo(buf.getvalue(), nl=False)


def _output_table(rows, columns=None):
    if not rows and not columns:
        return
    if columns is None:
        columns = list(rows[0].keys()) if rows else []
    if not columns:
        return
    # Calculate column widths
    widths = {col: len(str(col)) for col in columns}
    for row in rows:
        for col in columns:
            widths[col] = max(widths[col], len(str(row.get(col, ""))))
    # Header
    header = "  ".join(str(col).ljust(widths[col]) for col in columns)
    click.echo(header)
    # Separator
    sep = "  ".join("-" * widths[col] for col in columns)
    click.echo(sep)
    # Rows
    for row in rows:
        line = "  ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns)
        click.echo(line)


def _determine_output_format(fmt_csv, fmt_tsv, fmt_nl, fmt_table):
    if fmt_csv:
        return "csv"
    if fmt_tsv:
        return "tsv"
    if fmt_nl:
        return "nl"
    if fmt_table:
        return "table"
    return "json"


def output_format_options(f):
    """Decorator that adds --csv, --tsv, --nl, --table options to a command."""
    f = click.option(
        "fmt_table", "--table", "-t", is_flag=True, help="Output as ASCII table"
    )(f)
    f = click.option(
        "fmt_nl", "--nl", is_flag=True, help="Output as newline-delimited JSON"
    )(f)
    f = click.option("fmt_tsv", "--tsv", is_flag=True, help="Output as TSV")(f)
    f = click.option("fmt_csv", "--csv", is_flag=True, help="Output as CSV")(f)
    return f


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
    token = _resolve_token(
        token, url, config_dir / "auth.json", config_dir / "config.json"
    )
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
    token = _resolve_token(
        token, url, config_dir / "auth.json", config_dir / "config.json"
    )
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
    instance_alias = (
        _instance_alias_for_url(url, config_dir / "config.json")
        if not (
            instance
            and (instance.startswith("http://") or instance.startswith("https://"))
        )
        else None
    )
    if instance and not (
        instance.startswith("http://") or instance.startswith("https://")
    ):
        instance_alias = instance
    token = _resolve_token(
        token, url, config_dir / "auth.json", config_dir / "config.json"
    )
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
@output_format_options
def query(database, sql, instance, token, verbose, fmt_csv, fmt_tsv, fmt_nl, fmt_table):
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
    token = _resolve_token(
        token, url, config_dir / "auth.json", config_dir / "config.json"
    )
    query_url = url.rstrip("/") + "/" + database + ".json"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    params = {"sql": sql, "_shape": "objects"}
    if verbose:
        click.echo(query_url + "?" + urllib.parse.urlencode(params), err=True)
    response = httpx.get(
        query_url, params=params, headers=headers, follow_redirects=True
    )

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

    rows = response.json()["rows"]
    columns = response.json().get("columns")
    fmt = _determine_output_format(fmt_csv, fmt_tsv, fmt_nl, fmt_table)
    _output_rows(rows, fmt, columns)


def _do_insert(
    database,
    table,
    filepath,
    format_csv,
    format_tsv,
    format_json,
    format_nl,
    encoding,
    no_detect_types,
    replace,
    ignore,
    create,
    alter,
    pks,
    batch_size,
    interval,
    token,
    silent,
    verbose,
    instance,
    endpoint="insert",
):
    """Shared implementation for insert and upsert commands."""
    config_dir = get_config_dir()
    url = _resolve_instance(instance, config_dir / "config.json")
    token = _resolve_token(
        token, url, config_dir / "auth.json", config_dir / "config.json"
    )

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
        "filepath",
        type=click.Path("rb", readable=True, allow_dash=True, dir_okay=False),
    ),
    click.option(
        "-i", "--instance", default=None, help="Datasette instance URL or alias"
    ),
    click.option("format_csv", "--csv", is_flag=True, help="Input is CSV"),
    click.option("format_tsv", "--tsv", is_flag=True, help="Input is TSV"),
    click.option("format_json", "--json", is_flag=True, help="Input is JSON"),
    click.option(
        "format_nl", "--nl", is_flag=True, help="Input is newline-delimited JSON"
    ),
    click.option("--encoding", help="Character encoding for CSV/TSV"),
    click.option(
        "--no-detect-types", is_flag=True, help="Don't detect column types for CSV/TSV"
    ),
    click.option(
        "--alter", is_flag=True, help="Alter table to add any missing columns"
    ),
    click.option(
        "pks",
        "--pk",
        multiple=True,
        help="Columns to use as the primary key when creating the table",
    ),
    click.option(
        "--batch-size", type=int, default=100, help="Send rows in batches of this size"
    ),
    click.option(
        "--interval", type=float, default=10, help="Send batch at least every X seconds"
    ),
    click.option("--token", help="API token"),
    click.option("--silent", is_flag=True, help="Don't output progress"),
    click.option(
        "-v",
        "--verbose",
        is_flag=True,
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
@click.option(
    "--replace", is_flag=True, help="Replace rows with a matching primary key"
)
@click.option("--ignore", is_flag=True, help="Ignore rows with a matching primary key")
@click.option("--create", is_flag=True, help="Create table if it does not exist")
def insert(
    database,
    table,
    filepath,
    instance,
    format_csv,
    format_tsv,
    format_json,
    format_nl,
    encoding,
    no_detect_types,
    alter,
    pks,
    batch_size,
    interval,
    token,
    silent,
    verbose,
    replace,
    ignore,
    create,
):
    """
    Insert data into a remote Datasette instance

    Example usage:

    \b
        dclient insert main mytable data.csv --csv -i myapp
        dclient insert main mytable data.csv --csv --create --pk id
    """
    _do_insert(
        database,
        table,
        filepath,
        format_csv,
        format_tsv,
        format_json,
        format_nl,
        encoding,
        no_detect_types,
        replace,
        ignore,
        create,
        alter,
        pks,
        batch_size,
        interval,
        token,
        silent,
        verbose,
        instance,
        endpoint="insert",
    )


@cli.command()
@_apply_options(_insert_options)
def upsert(
    database,
    table,
    filepath,
    instance,
    format_csv,
    format_tsv,
    format_json,
    format_nl,
    encoding,
    no_detect_types,
    alter,
    pks,
    batch_size,
    interval,
    token,
    silent,
    verbose,
):
    """
    Upsert data into a remote Datasette instance

    Example usage:

    \b
        dclient upsert main mytable data.csv --csv -i myapp
    """
    _do_insert(
        database,
        table,
        filepath,
        format_csv,
        format_tsv,
        format_json,
        format_nl,
        encoding,
        no_detect_types,
        False,
        False,
        False,
        alter,
        pks,
        batch_size,
        interval,
        token,
        silent,
        verbose,
        instance,
        endpoint="upsert",
    )


@cli.command(name="create-table")
@click.argument("database")
@click.argument("table_name")
@click.option(
    "--column",
    "-c",
    "column_defs",
    multiple=True,
    nargs=2,
    help="Column definition: name type (e.g. --column id integer --column name text)",
)
@click.option(
    "pks",
    "--pk",
    multiple=True,
    help="Column(s) to use as primary key",
)
@click.option("-i", "--instance", default=None, help="Datasette instance URL or alias")
@click.option("--token", help="API token")
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Verbose output: show HTTP request and response",
)
def create_table(database, table_name, column_defs, pks, instance, token, verbose):
    """
    Create a new empty table with an explicit schema

    Example usage:

    \b
        dclient create-table mydb dogs \\
          --column id integer --column name text --pk id
    """
    config_dir = get_config_dir()
    url = _resolve_instance(instance, config_dir / "config.json")
    token = _resolve_token(
        token, url, config_dir / "auth.json", config_dir / "config.json"
    )

    if not column_defs:
        raise click.ClickException("Provide at least one --column definition")

    columns = [{"name": name, "type": typ} for name, typ in column_defs]
    data = {"table": table_name, "columns": columns}
    if pks:
        if len(pks) == 1:
            data["pk"] = pks[0]
        else:
            data["pks"] = list(pks)

    api_url = url.rstrip("/") + "/" + database + "/-/create"
    if verbose:
        click.echo("POST {}".format(api_url), err=True)
        click.echo(textwrap.indent(json.dumps(data, indent=2), "  "), err=True)
    response = httpx.post(
        api_url,
        headers={
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        },
        json=data,
        timeout=30.0,
    )
    if verbose:
        click.echo(str(response), err=True)
    if str(response.status_code)[0] != "2":
        if "/json" in response.headers.get("content-type", ""):
            resp_data = response.json()
            if "errors" in resp_data:
                raise click.ClickException("\n".join(resp_data["errors"]))
        response.raise_for_status()
    click.echo(json.dumps(response.json(), indent=2))


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
    instance_alias = (
        _instance_alias_for_url(url, config_dir / "config.json")
        if not (
            instance
            and (instance.startswith("http://") or instance.startswith("https://"))
        )
        else None
    )
    if instance and not (
        instance.startswith("http://") or instance.startswith("https://")
    ):
        instance_alias = instance
    token = _resolve_token(
        token, url, config_dir / "auth.json", config_dir / "config.json"
    )
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
    token = _resolve_token(
        token, url, config_dir / "auth.json", config_dir / "config.json"
    )
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
    token = _resolve_token(
        token, url, config_dir / "auth.json", config_dir / "config.json"
    )
    response = _make_request(url, token, "/-/actor.json")
    response.raise_for_status()
    click.echo(json.dumps(response.json(), indent=4))


@cli.command(name="default_query", hidden=True)
@click.argument("sql")
@click.option("-i", "--instance", default=None, help="Datasette instance URL or alias")
@click.option("-d", "--database", default=None, help="Database name")
@click.option("--token", help="API token")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output: show HTTP request")
@output_format_options
def default_query(
    sql, instance, database, token, verbose, fmt_csv, fmt_tsv, fmt_nl, fmt_table
):
    """Run a SQL query using default instance and database."""
    config_dir = get_config_dir()
    url = _resolve_instance(instance, config_dir / "config.json")
    instance_alias = (
        _instance_alias_for_url(url, config_dir / "config.json")
        if not (
            instance
            and (instance.startswith("http://") or instance.startswith("https://"))
        )
        else None
    )
    if instance and not (
        instance.startswith("http://") or instance.startswith("https://")
    ):
        instance_alias = instance
    token = _resolve_token(
        token, url, config_dir / "auth.json", config_dir / "config.json"
    )
    db = _resolve_database(database, instance_alias, config_dir / "config.json")
    query_url = url.rstrip("/") + "/" + db + ".json"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    params = {"sql": sql, "_shape": "objects"}
    if verbose:
        click.echo(query_url + "?" + urllib.parse.urlencode(params), err=True)
    response = httpx.get(
        query_url, params=params, headers=headers, follow_redirects=True
    )

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

    rows = response.json()["rows"]
    columns = response.json().get("columns")
    fmt = _determine_output_format(fmt_csv, fmt_tsv, fmt_nl, fmt_table)
    _output_rows(rows, fmt, columns)


@cli.command()
@click.option("--json", "_json", is_flag=True, help="Output raw JSON")
def instances(_json):
    """
    List known instances from the config

    Example usage:

    \b
        dclient instances
        dclient instances --json
    """
    config_file = get_config_dir() / "config.json"
    config = _load_config(config_file)
    inst_map = config.get("instances", {})
    default = config.get("default_instance")
    if _json:
        click.echo(json.dumps(config, indent=2))
    else:
        for name, inst in inst_map.items():
            marker = "* " if name == default else "  "
            db_info = (
                f" (db: {inst['default_database']})"
                if inst.get("default_database")
                else ""
            )
            click.echo(f"{marker}{name} = {inst['url']}{db_info}")


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
            db_info = (
                f" (db: {inst['default_database']})"
                if inst.get("default_database")
                else ""
            )
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


def _resolve_instance_key(alias_or_url, config):
    instances = config.get("instances", {})
    if alias_or_url in instances:
        return alias_or_url
    if alias_or_url.startswith("http://") or alias_or_url.startswith("https://"):
        normalized = alias_or_url.rstrip("/")
        for name, inst in instances.items():
            if inst.get("url", "").rstrip("/") == normalized:
                return name
        raise click.ClickException(f"No such instance URL: {alias_or_url}")
    raise click.ClickException(f"No such alias: {alias_or_url}")


# -- default command group --


@cli.group()
def default():
    "Manage default instance and database"


@default.command(name="instance")
@click.argument("alias_or_url", required=False, default=None)
@click.option("--clear", is_flag=True, help="Clear default instance")
def default_instance(alias_or_url, clear):
    """
    Set or show the default instance

    Example usage:

    \b
        dclient default instance prod
        dclient default instance https://myapp.datasette.cloud
        dclient default instance
        dclient default instance --clear
    """
    config_file = get_config_dir() / "config.json"
    config = _load_config(config_file)
    if clear:
        config["default_instance"] = None
        _save_config(config_file, config)
    elif alias_or_url:
        if alias_or_url.startswith("http://") or alias_or_url.startswith("https://"):
            try:
                key = _resolve_instance_key(alias_or_url, config)
            except click.ClickException:
                key = alias_or_url.rstrip("/")
        else:
            key = _resolve_instance_key(alias_or_url, config)
        config["default_instance"] = key
        _save_config(config_file, config)
    else:
        default = config.get("default_instance")
        if default:
            click.echo(default)
        else:
            click.echo("No default instance set")


@default.command(name="database")
@click.argument("alias_or_url")
@click.argument("db", required=False, default=None)
@click.option("--clear", is_flag=True, help="Clear default database for this instance")
def default_database(alias_or_url, db, clear):
    """
    Set or show the default database for an instance

    Example usage:

    \b
        dclient default database prod main
        dclient default database https://myapp.datasette.cloud main
        dclient default database prod
        dclient default database prod --clear
    """
    config_file = get_config_dir() / "config.json"
    config = _load_config(config_file)
    instance_key = _resolve_instance_key(alias_or_url, config)
    if clear:
        config["instances"][instance_key]["default_database"] = None
        _save_config(config_file, config)
    elif db:
        config["instances"][instance_key]["default_database"] = db
        _save_config(config_file, config)
    else:
        default_db = config["instances"][instance_key].get("default_database")
        if default_db:
            click.echo(default_db)
        else:
            click.echo(f"No default database set for {instance_key}")


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
    token = _resolve_token(
        token, url, config_dir / "auth.json", config_dir / "config.json"
    )
    response = _make_request(url, token, "/-/actor.json")
    response.raise_for_status()
    click.echo(json.dumps(response.json(), indent=4))


# -- login command (OAuth device flow) --


@cli.command()
@click.argument("alias_or_url", required=False, default=None)
@click.option("--scope", default=None, help="JSON scope array")
def login(alias_or_url, scope):
    """
    Authenticate with a Datasette instance using OAuth

    Uses the OAuth device flow: opens a URL in your browser where you
    approve access, then saves the resulting API token.

    Example usage:

    \b
        dclient login https://simon.datasette.cloud/
        dclient login myalias
        dclient login
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"

    if alias_or_url is None:
        click.echo("Enter the URL of your Datasette instance, or an alias you have")
        click.echo("already configured with 'dclient alias add'.\n")
        alias_or_url = click.prompt("Instance URL or alias")

    # Resolve alias to URL if needed
    if alias_or_url.startswith("http://") or alias_or_url.startswith("https://"):
        url = alias_or_url
        auth_key = alias_or_url
    else:
        url = _resolve_instance(alias_or_url, config_file)
        auth_key = alias_or_url

    # Ensure trailing slash
    if not url.endswith("/"):
        url += "/"

    # Step 1: Request device code
    device_url = url + "-/oauth/device"
    data = {}
    if scope:
        data["scope"] = scope
    response = httpx.post(device_url, data=data, timeout=30.0)
    if response.status_code != 200:
        raise click.ClickException(
            f"Failed to start login flow: {response.status_code} from {device_url}"
        )
    device_data = response.json()
    device_code = device_data["device_code"]
    user_code = device_data["user_code"]
    verification_uri = device_data["verification_uri"]
    interval = device_data.get("interval", 5)

    # Step 2: Show instructions
    click.echo(f"\nOpen this URL in your browser:\n")
    click.echo(f"    {verification_uri}\n")
    click.echo(f"Enter this code: {user_code}\n")
    click.echo("Waiting for authorization...", nl=False)

    # Step 3: Poll for token
    token_url = url + "-/oauth/token"
    while True:
        time.sleep(interval)
        click.echo(".", nl=False)
        token_response = httpx.post(
            token_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
            },
            timeout=30.0,
        )
        token_data = token_response.json()
        if "access_token" in token_data:
            break
        error = token_data.get("error")
        if error == "authorization_pending":
            continue
        elif error == "access_denied":
            click.echo()
            raise click.ClickException("Authorization denied.")
        elif error == "expired_token":
            click.echo()
            raise click.ClickException("Device code expired. Run login again.")
        else:
            click.echo()
            raise click.ClickException(f"Unexpected error: {error}")

    # Step 4: Save token
    click.echo()
    access_token = token_data["access_token"]
    auth_file = config_dir / "auth.json"
    auths = _load_auths(auth_file)
    auths[auth_key] = access_token
    auth_file.write_text(json.dumps(auths, indent=4))
    click.echo(f"Login successful. Token saved for {auth_key}")

    # Step 5: Set defaults if not already configured
    config = _load_config(config_file)
    default_alias = config.get("default_instance")
    has_default_instance = default_alias is not None
    has_default_db = bool(
        config.get("instances", {}).get(default_alias or "", {}).get("default_database")
    )
    if has_default_instance and has_default_db:
        return
    # Find alias for this instance, or use the auth_key (URL) as the instance key
    instance_key = _instance_alias_for_url(url, config_file) or auth_key
    # Ensure instance entry exists in config
    if instance_key not in config.get("instances", {}):
        config.setdefault("instances", {})[instance_key] = {
            "url": url.rstrip("/"),
            "default_database": None,
        }
    # Set as default instance if none configured
    if not has_default_instance:
        config["default_instance"] = instance_key
        click.echo(f"Set default instance to {instance_key}")
    # Query databases and set default database if none configured
    if not has_default_db:
        try:
            db_response = _make_request(url, access_token, "/.json")
            if db_response.status_code == 200:
                db_data = db_response.json()
                if isinstance(db_data, list):
                    databases_list = db_data
                else:
                    databases_list = db_data.get("databases", [])
                if isinstance(databases_list, dict):
                    databases_list = list(databases_list.values())
                db_names = [
                    db["name"] if isinstance(db, dict) else db for db in databases_list
                ]
                if db_names:
                    if len(db_names) == 1:
                        default_db = db_names[0]
                    elif "data" in db_names:
                        default_db = "data"
                    else:
                        default_db = db_names[0]
                    config["instances"][instance_key]["default_database"] = default_db
                    click.echo(f"Set default database to {default_db}")
        except Exception:
            pass  # Don't fail login if databases check fails
    _save_config(config_file, config)


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
    *,
    url,
    table,
    batch,
    token,
    create,
    alter,
    pks,
    replace,
    ignore,
    verbose,
    endpoint="insert",
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
