import click
import csv
import httpx
import io
import json
import pathlib
from sqlite_utils.utils import rows_from_file, Format, TypeTracker, progressbar
import sys
import textwrap
import time
from .utils import token_for_url
import urllib


def get_config_dir():
    return pathlib.Path(click.get_app_dir("io.datasette.dclient"))


# --- Shared infrastructure ---


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


def _resolve_url(url_or_alias):
    """Resolve an alias to a URL, or return the input unchanged."""
    aliases_file = get_config_dir() / "aliases.json"
    aliases = _load_aliases(aliases_file)
    if url_or_alias in aliases:
        return aliases[url_or_alias]
    return url_or_alias


def _resolve_token(url, token=None):
    """Resolve a token from CLI arg, env var, or auth.json."""
    if token:
        return token
    env_token = click.get_current_context().obj.get("env_token") if click.get_current_context().obj else None
    if env_token:
        return env_token
    return token_for_url(url, _load_auths(get_config_dir() / "auth.json"))


def _make_headers(token):
    """Build request headers with optional auth."""
    headers = {}
    if token:
        headers["Authorization"] = "Bearer {}".format(token)
    return headers


def _api_get(url, token=None, params=None, verbose=False):
    """Make an authenticated GET request and return parsed JSON."""
    headers = _make_headers(token)
    if verbose:
        full_url = url
        if params:
            full_url += "?" + urllib.parse.urlencode(params, doseq=True)
        click.echo(full_url, err=True)
    response = httpx.get(url, params=params, headers=headers, timeout=40.0)
    if response.status_code != 200:
        _raise_api_error(response)
    try:
        data = response.json()
    except json.JSONDecodeError:
        raise click.ClickException("Response was not valid JSON")
    if isinstance(data, dict) and data.get("ok") is False:
        _raise_from_data(data)
    return data


def _api_post(url, data, token=None, verbose=False):
    """Make an authenticated POST request and return parsed JSON."""
    headers = _make_headers(token)
    headers["Content-Type"] = "application/json"
    if verbose:
        click.echo("POST {}".format(url), err=True)
        click.echo(textwrap.indent(json.dumps(data, indent=2), "  "), err=True)
    response = httpx.post(url, headers=headers, json=data, timeout=40.0)
    if verbose:
        click.echo(str(response), err=True)
    if str(response.status_code)[0] != "2":
        if "json" in response.headers.get("content-type", ""):
            resp_data = response.json()
            if "errors" in resp_data:
                raise click.ClickException("\n".join(resp_data["errors"]))
            _raise_from_data(resp_data)
        response.raise_for_status()
    response_data = response.json()
    if verbose:
        click.echo(textwrap.indent(json.dumps(response_data, indent=2), "  "), err=True)
    return response_data


def _raise_api_error(response):
    """Raise a ClickException from a non-200 response."""
    try:
        data = response.json()
    except json.JSONDecodeError:
        raise click.ClickException(
            "{} status code. Response was not valid JSON".format(response.status_code)
        )
    bits = []
    if data.get("title"):
        bits.append(data["title"])
    if data.get("error"):
        bits.append(data["error"])
    raise click.ClickException(
        "{} status code. {}".format(response.status_code, ": ".join(bits))
    )


def _raise_from_data(data):
    """Raise a ClickException from a JSON error response."""
    bits = []
    if data.get("title"):
        bits.append(data["title"])
    if data.get("error"):
        bits.append(data["error"])
    if data.get("errors"):
        bits.extend(data["errors"])
    if not bits:
        bits = [json.dumps(data)]
    raise click.ClickException(": ".join(bits))


def _output_rows(rows, output_format, nl=False, cols=None):
    """Output rows in the specified format."""
    if output_format == "json":
        click.echo(json.dumps(rows, indent=2))
    elif output_format == "nl":
        for row in rows:
            click.echo(json.dumps(row))
    elif output_format == "csv":
        _output_csv(rows, cols)
    elif output_format == "tsv":
        _output_csv(rows, cols, delimiter="\t")
    elif output_format == "table":
        _output_table(rows, cols)
    else:
        click.echo(json.dumps(rows, indent=2))


def _output_csv(rows, cols=None, delimiter=","):
    """Write rows as CSV/TSV to stdout."""
    if not rows:
        return
    if cols is None:
        cols = list(rows[0].keys())
    writer = csv.DictWriter(sys.stdout, fieldnames=cols, delimiter=delimiter, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)


def _output_table(rows, cols=None):
    """Write rows as a simple aligned text table."""
    if not rows:
        return
    if cols is None:
        cols = list(rows[0].keys())
    # Calculate column widths
    widths = {col: len(col) for col in cols}
    str_rows = []
    for row in rows:
        str_row = {}
        for col in cols:
            val = str(row.get(col, "")) if row.get(col) is not None else ""
            str_row[col] = val
            widths[col] = max(widths[col], len(val))
        str_rows.append(str_row)
    # Header
    header = "  ".join(col.ljust(widths[col]) for col in cols)
    click.echo(header)
    click.echo("  ".join("-" * widths[col] for col in cols))
    for str_row in str_rows:
        click.echo("  ".join(str_row[col].ljust(widths[col]) for col in cols))


def _determine_format(fmt_csv, fmt_tsv, fmt_json, fmt_nl, fmt_table, default="json"):
    """Determine output format from flags."""
    if fmt_csv:
        return "csv"
    if fmt_tsv:
        return "tsv"
    if fmt_json:
        return "json"
    if fmt_nl:
        return "nl"
    if fmt_table:
        return "table"
    return default


# --- CLI ---


@click.group()
@click.version_option()
@click.pass_context
def cli(ctx):
    "A client CLI utility for Datasette instances"
    ctx.ensure_object(dict)
    import os

    ctx.obj["env_token"] = os.environ.get("DCLIENT_TOKEN")
    ctx.obj["env_url"] = os.environ.get("DCLIENT_URL")


def _resolve_url_with_env(url_or_alias):
    """Resolve URL, falling back to DCLIENT_URL env var."""
    if url_or_alias:
        return _resolve_url(url_or_alias)
    ctx = click.get_current_context()
    env_url = ctx.obj.get("env_url") if ctx.obj else None
    if env_url:
        return env_url
    raise click.ClickException("No URL provided and DCLIENT_URL not set")


# --- Output format options (shared decorator) ---


def output_format_options(f):
    """Add --csv, --tsv, --json, --nl, --table output options."""
    f = click.option("fmt_table", "--table", is_flag=True, help="Output as text table")(f)
    f = click.option("fmt_nl", "--nl", is_flag=True, help="Output as newline-delimited JSON")(f)
    f = click.option("fmt_json", "--json", is_flag=True, help="Output as JSON (default)")(f)
    f = click.option("fmt_tsv", "--tsv", is_flag=True, help="Output as TSV")(f)
    f = click.option("fmt_csv", "--csv", is_flag=True, help="Output as CSV")(f)
    return f


# --- query command ---


@cli.command()
@click.argument("url_or_alias")
@click.argument("sql")
@click.option("--token", help="API token")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output: show HTTP request")
@output_format_options
@click.pass_context
def query(ctx, url_or_alias, sql, token, verbose, fmt_csv, fmt_tsv, fmt_json, fmt_nl, fmt_table):
    """
    Run a SQL query against a Datasette database URL

    Returns a JSON array of objects

    Example usage:

    \b
        dclient query \\
          https://datasette.io/content \\
          'select * from news limit 10'
    """
    url = _resolve_url_with_env(url_or_alias)
    if not url.endswith(".json"):
        url += ".json"
    token = _resolve_token(url, token)
    data = _api_get(url, token=token, params={"sql": sql, "_shape": "objects"}, verbose=verbose)
    output_format = _determine_format(fmt_csv, fmt_tsv, fmt_json, fmt_nl, fmt_table)
    _output_rows(data["rows"], output_format)


# --- databases command ---


@cli.command()
@click.argument("url_or_alias", required=False)
@click.option("--token", help="API token")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@output_format_options
@click.pass_context
def databases(ctx, url_or_alias, token, verbose, fmt_csv, fmt_tsv, fmt_json, fmt_nl, fmt_table):
    """
    List databases on a Datasette instance

    Example usage:

    \b
        dclient databases https://latest.datasette.io
    """
    url = _resolve_url_with_env(url_or_alias)
    # Ensure we hit the instance root
    api_url = url.rstrip("/") + "/-/databases.json"
    token = _resolve_token(url, token)
    data = _api_get(api_url, token=token, verbose=verbose)
    output_format = _determine_format(fmt_csv, fmt_tsv, fmt_json, fmt_nl, fmt_table)
    if output_format == "table":
        rows = []
        for db in data:
            rows.append({
                "name": db["name"],
                "path": db.get("path", ""),
                "is_mutable": db.get("is_mutable", ""),
            })
        _output_rows(rows, "table")
    elif output_format == "json":
        click.echo(json.dumps(data, indent=2))
    else:
        _output_rows(data, output_format)


# --- tables command ---


@cli.command()
@click.argument("url_or_alias", required=False)
@click.option("--token", help="API token")
@click.option("--views", is_flag=True, help="Include views")
@click.option("--schema", is_flag=True, help="Show CREATE TABLE SQL")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@output_format_options
@click.pass_context
def tables(ctx, url_or_alias, token, views, schema, verbose, fmt_csv, fmt_tsv, fmt_json, fmt_nl, fmt_table):
    """
    List tables in a Datasette database

    Example usage:

    \b
        dclient tables https://latest.datasette.io/fixtures
    """
    url = _resolve_url_with_env(url_or_alias)
    api_url = url.rstrip("/") + ".json"
    token = _resolve_token(url, token)
    data = _api_get(api_url, token=token, verbose=verbose)
    output_format = _determine_format(fmt_csv, fmt_tsv, fmt_json, fmt_nl, fmt_table)

    result_tables = data.get("tables", []) if isinstance(data, dict) else data
    if not views:
        result_tables = [t for t in result_tables if not t.get("hidden")]

    if schema:
        # Fetch schema for the database
        schema_url = url.rstrip("/") + "/-/schema.json"
        schema_data = _api_get(schema_url, token=token, verbose=verbose)
        schema_map = {}
        if isinstance(schema_data, dict):
            for item in schema_data.get("tables", []):
                schema_map[item["name"]] = item.get("schema", "")
        for t in result_tables:
            t["schema"] = schema_map.get(t["name"], "")

    if output_format == "json":
        click.echo(json.dumps(result_tables, indent=2))
    elif output_format == "table":
        rows = []
        for t in result_tables:
            row = {
                "name": t["name"],
                "rows": str(t.get("count", t.get("rows_count", ""))),
                "columns": ", ".join(t.get("columns", [])),
            }
            if schema:
                row["schema"] = t.get("schema", "")
            rows.append(row)
        _output_rows(rows, "table")
    else:
        _output_rows(result_tables, output_format)


# --- schema command ---


@cli.command()
@click.argument("url_or_alias", required=False)
@click.option("--token", help="API token")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.pass_context
def schema(ctx, url_or_alias, token, verbose):
    """
    Show the SQL schema for a database or table

    Example usage:

    \b
        dclient schema https://latest.datasette.io/fixtures
        dclient schema https://latest.datasette.io/fixtures/facetable
    """
    url = _resolve_url_with_env(url_or_alias)
    token = _resolve_token(url, token)
    schema_url = url.rstrip("/") + "/-/schema.json"
    data = _api_get(schema_url, token=token, verbose=verbose)
    if isinstance(data, dict) and "tables" in data:
        for t in data["tables"]:
            click.echo(t.get("schema", "") + ";")
            click.echo()
    elif isinstance(data, dict) and "schema" in data:
        click.echo(data["schema"] + ";")
    else:
        click.echo(json.dumps(data, indent=2))


# --- rows command ---


@cli.command()
@click.argument("url_or_alias", required=False)
@click.option("--token", help="API token")
@click.option("-w", "--where", "where_clauses", multiple=True, help="Filter: column__op=value (e.g. age__gt=30)")
@click.option("--where-sql", "where_sql", multiple=True, help="Raw SQL WHERE clause")
@click.option("--search", help="Full-text search query")
@click.option("--sort", help="Sort by column (ascending)")
@click.option("--sort-desc", help="Sort by column (descending)")
@click.option("--col", "columns", multiple=True, help="Include only these columns")
@click.option("--nocol", "nocolumns", multiple=True, help="Exclude these columns")
@click.option("--facet", "facets", multiple=True, help="Facet by column")
@click.option("--size", type=int, help="Number of rows per page")
@click.option("--all", "fetch_all", is_flag=True, help="Fetch all pages")
@click.option("--limit", type=int, help="Maximum total rows to return")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@output_format_options
@click.pass_context
def rows(ctx, url_or_alias, token, where_clauses, where_sql, search, sort,
         sort_desc, columns, nocolumns, facets, size, fetch_all, limit, verbose,
         fmt_csv, fmt_tsv, fmt_json, fmt_nl, fmt_table):
    """
    Browse rows in a Datasette table with filtering and sorting

    Example usage:

    \b
        dclient rows https://latest.datasette.io/fixtures/facetable
        dclient rows https://latest.datasette.io/fixtures/facetable -w state=CA
        dclient rows https://latest.datasette.io/fixtures/facetable --sort city
        dclient rows https://latest.datasette.io/fixtures/facetable --search text
    """
    url = _resolve_url_with_env(url_or_alias)
    token = _resolve_token(url, token)
    output_format = _determine_format(fmt_csv, fmt_tsv, fmt_json, fmt_nl, fmt_table)

    # Build query params
    params = [("_shape", "objects"), ("_extra", "next_url")]
    for w in where_clauses:
        if "=" in w:
            key, _, value = w.partition("=")
            params.append((key, value))
        else:
            params.append(("_where", w))
    for w in where_sql:
        params.append(("_where", w))
    if search:
        params.append(("_search", search))
    if sort:
        params.append(("_sort", sort))
    if sort_desc:
        params.append(("_sort_desc", sort_desc))
    for col in columns:
        params.append(("_col", col))
    for col in nocolumns:
        params.append(("_nocol", col))
    for facet in facets:
        params.append(("_facet", facet))
    if size:
        params.append(("_size", str(size)))

    api_url = url.rstrip("/") + ".json"
    all_rows = []
    total = 0
    page_url = api_url

    while True:
        data = _api_get(page_url, token=token, params=params if page_url == api_url else None, verbose=verbose)
        page_rows = data.get("rows", [])
        if limit:
            remaining = limit - total
            page_rows = page_rows[:remaining]
        all_rows.extend(page_rows)
        total += len(page_rows)

        if limit and total >= limit:
            break

        next_url = data.get("next_url")
        if not fetch_all or not next_url:
            break
        page_url = next_url
        params = None  # next_url includes params

    # Show facets if requested
    facet_results = data.get("facet_results") if facets else None
    if facet_results:
        click.echo("Facets:", err=True)
        for facet_name, facet_info in facet_results.items():
            click.echo("  {}:".format(facet_name), err=True)
            results_list = facet_info.get("results", facet_info) if isinstance(facet_info, dict) else facet_info
            if isinstance(results_list, list):
                for item in results_list:
                    click.echo("    {} ({})".format(item.get("value", ""), item.get("count", "")), err=True)
        click.echo(err=True)

    _output_rows(all_rows, output_format)


# --- get command ---


@cli.command()
@click.argument("url_or_alias", required=False)
@click.argument("pk_values")
@click.option("--token", help="API token")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.pass_context
def get(ctx, url_or_alias, pk_values, token, verbose):
    """
    Fetch a single row by primary key

    Example usage:

    \b
        dclient get https://latest.datasette.io/fixtures/facetable 1
        dclient get https://latest.datasette.io/fixtures/compound_pk a,b
    """
    url = _resolve_url_with_env(url_or_alias)
    token = _resolve_token(url, token)
    api_url = url.rstrip("/") + "/" + pk_values + ".json"
    data = _api_get(api_url, token=token, params={"_shape": "objects"}, verbose=verbose)
    rows = data.get("rows", [data] if isinstance(data, dict) else data)
    if rows:
        click.echo(json.dumps(rows[0], indent=2))
    else:
        raise click.ClickException("Row not found")


# --- insert command ---


@cli.command()
@click.argument("url_or_alias")
@click.argument("table")
@click.argument(
    "filepath", type=click.Path("rb", readable=True, allow_dash=True, dir_okay=False)
)
@click.option("format_csv", "--csv", is_flag=True, help="Input is CSV")
@click.option("format_tsv", "--tsv", is_flag=True, help="Input is TSV")
@click.option("format_json", "--json", is_flag=True, help="Input is JSON")
@click.option("format_nl", "--nl", is_flag=True, help="Input is newline-delimited JSON")
@click.option("--encoding", help="Character encoding for CSV/TSV")
@click.option(
    "--no-detect-types", is_flag=True, help="Don't detect column types for CSV/TSV"
)
@click.option(
    "--replace", is_flag=True, help="Replace rows with a matching primary key"
)
@click.option("--ignore", is_flag=True, help="Ignore rows with a matching primary key")
@click.option("--create", is_flag=True, help="Create table if it does not exist")
@click.option("--alter", is_flag=True, help="Alter table to add any missing columns")
@click.option(
    "pks",
    "--pk",
    multiple=True,
    help="Columns to use as the primary key when creating the table",
)
@click.option(
    "--batch-size", type=int, default=100, help="Send rows in batches of this size"
)
@click.option(
    "--interval", type=float, default=10, help="Send batch at least every X seconds"
)
@click.option("--token", "-t", help="API token")
@click.option("--silent", is_flag=True, help="Don't output progress")
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Verbose output: show HTTP request and response",
)
def insert(
    url_or_alias,
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
):
    """
    Insert data into a remote Datasette instance

    Example usage:

    \b
        dclient insert \\
          https://private.datasette.cloud/data \\
          mytable data.csv --pk id --create
    """
    url = _resolve_url(url_or_alias)
    token = _resolve_token(url, token)

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
                url=url,
                table=table,
                batch=batch,
                token=token,
                create=create,
                alter=alter,
                pks=pks,
                replace=replace,
                ignore=ignore,
                verbose=verbose,
            )


# --- upsert command ---


@cli.command()
@click.argument("url_or_alias")
@click.argument("table")
@click.argument(
    "filepath", type=click.Path("rb", readable=True, allow_dash=True, dir_okay=False)
)
@click.option("format_csv", "--csv", is_flag=True, help="Input is CSV")
@click.option("format_tsv", "--tsv", is_flag=True, help="Input is TSV")
@click.option("format_json", "--json", is_flag=True, help="Input is JSON")
@click.option("format_nl", "--nl", is_flag=True, help="Input is newline-delimited JSON")
@click.option("--encoding", help="Character encoding for CSV/TSV")
@click.option(
    "--no-detect-types", is_flag=True, help="Don't detect column types for CSV/TSV"
)
@click.option("--alter", is_flag=True, help="Alter table to add any missing columns")
@click.option(
    "--batch-size", type=int, default=100, help="Send rows in batches of this size"
)
@click.option(
    "--interval", type=float, default=10, help="Send batch at least every X seconds"
)
@click.option("--token", "-t", help="API token")
@click.option("--silent", is_flag=True, help="Don't output progress")
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Verbose output: show HTTP request and response",
)
def upsert(
    url_or_alias,
    table,
    filepath,
    format_csv,
    format_tsv,
    format_json,
    format_nl,
    encoding,
    no_detect_types,
    alter,
    batch_size,
    interval,
    token,
    silent,
    verbose,
):
    """
    Upsert data into a remote Datasette table

    Rows with matching primary keys will be updated; others will be inserted.
    Each row must include the primary key column(s).

    Example usage:

    \b
        dclient upsert \\
          https://private.datasette.cloud/data \\
          mytable data.csv
    """
    url = _resolve_url(url_or_alias)
    token = _resolve_token(url, token)

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

    with progressbar(
        length=file_size,
        label="Upserting rows",
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
            data = {"rows": batch}
            if alter:
                data["alter"] = True
            upsert_url = "{}/{}/-/upsert".format(url, table)
            _api_post(upsert_url, data, token=token, verbose=verbose)


# --- update command ---


@cli.command()
@click.argument("url_or_alias")
@click.argument("pk_values")
@click.argument("updates", nargs=-1)
@click.option("--token", help="API token")
@click.option("--alter", is_flag=True, help="Alter table to add any missing columns")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def update(url_or_alias, pk_values, updates, token, alter, verbose):
    """
    Update a row by primary key

    Pass key=value pairs to set column values.

    Example usage:

    \b
        dclient update https://example.com/db/table 42 name=Alice age=30
    """
    url = _resolve_url(url_or_alias)
    token = _resolve_token(url, token)

    if not updates:
        raise click.ClickException("Provide at least one key=value pair")

    update_dict = {}
    for pair in updates:
        if "=" not in pair:
            raise click.ClickException("Invalid key=value pair: {}".format(pair))
        key, _, value = pair.partition("=")
        # Try to parse as JSON for numbers, booleans, null
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            pass
        update_dict[key] = value

    data = {"update": update_dict}
    if alter:
        data["alter"] = True

    api_url = "{}/{}/-/update".format(url.rstrip("/"), pk_values)
    result = _api_post(api_url, data, token=token, verbose=verbose)
    click.echo(json.dumps(result, indent=2))


# --- delete command ---


@cli.command()
@click.argument("url_or_alias")
@click.argument("pk_values")
@click.option("--token", help="API token")
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def delete(url_or_alias, pk_values, token, yes, verbose):
    """
    Delete a row by primary key

    Example usage:

    \b
        dclient delete https://example.com/db/table 42
        dclient delete https://example.com/db/table 42 --yes
    """
    url = _resolve_url(url_or_alias)
    token = _resolve_token(url, token)

    if not yes:
        click.confirm("Delete row {}?".format(pk_values), abort=True)

    api_url = "{}/{}/-/delete".format(url.rstrip("/"), pk_values)
    result = _api_post(api_url, {}, token=token, verbose=verbose)
    click.echo(json.dumps(result, indent=2))


# --- drop command ---


@cli.command()
@click.argument("url_or_alias")
@click.option("--token", help="API token")
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def drop(url_or_alias, token, yes, verbose):
    """
    Drop a table

    Example usage:

    \b
        dclient drop https://example.com/db/table
        dclient drop https://example.com/db/table --yes
    """
    url = _resolve_url(url_or_alias)
    token = _resolve_token(url, token)

    api_url = url.rstrip("/") + "/-/drop"

    if not yes:
        # First request to get row count
        info = _api_post(api_url, {}, token=token, verbose=verbose)
        row_count = info.get("row_count", "unknown")
        table_name = info.get("table", url.rstrip("/").split("/")[-1])
        click.confirm("Drop table {} ({} rows)?".format(table_name, row_count), abort=True)

    result = _api_post(api_url, {"confirm": True}, token=token, verbose=verbose)
    click.echo(json.dumps(result, indent=2))


# --- create-table command ---


@cli.command(name="create-table")
@click.argument("url_or_alias")
@click.argument("table_name")
@click.option(
    "--column", "column_defs", multiple=True, nargs=2,
    help="Column definition: name type (e.g. --column id integer --column name text)"
)
@click.option(
    "pks", "--pk", multiple=True,
    help="Column(s) to use as primary key"
)
@click.option("--token", help="API token")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def create_table(url_or_alias, table_name, column_defs, pks, token, verbose):
    """
    Create a new empty table with explicit schema

    Example usage:

    \b
        dclient create-table https://example.com/db mytable \\
          --column id integer --column name text --pk id
    """
    url = _resolve_url(url_or_alias)
    token = _resolve_token(url, token)

    if not column_defs:
        raise click.ClickException("Provide at least one --column definition")

    columns = [{"name": name, "type": typ} for name, typ in column_defs]
    data = {"table": table_name, "columns": columns}
    if pks:
        if len(pks) == 1:
            data["pk"] = pks[0]
        else:
            data["pks"] = list(pks)

    api_url = url.rstrip("/") + "/-/create"
    result = _api_post(api_url, data, token=token, verbose=verbose)
    click.echo(json.dumps(result, indent=2))


# --- actor command ---


@cli.command()
@click.argument("url_or_alias", required=False)
@click.option("--token", help="API token")
@click.pass_context
def actor(ctx, url_or_alias, token):
    """
    Show the actor represented by an API token

    Example usage:

    \b
        dclient actor https://latest.datasette.io/fixtures
    """
    url = _resolve_url_with_env(url_or_alias)

    if not (url.startswith("http://") or url.startswith("https://")):
        raise click.ClickException("Invalid URL: " + url)

    token = _resolve_token(url, token)

    url_bits = url.split("/")
    url_bits[-1] = "-/actor.json"
    actor_url = "/".join(url_bits)
    response = httpx.get(
        actor_url, headers={"Authorization": "Bearer {}".format(token)}, timeout=40.0
    )
    response.raise_for_status()
    click.echo(json.dumps(response.json(), indent=4))


# --- alias commands ---


@cli.group()
def alias():
    "Manage aliases for different instances"


@alias.command(name="list")
@click.option("_json", "--json", is_flag=True, help="Output raw JSON")
def list_(_json):
    """
    List aliases

    Example usage:

    \b
        dclient aliases list
    """
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
    """
    Add an alias

    Example usage:

    \b
        dclient alias add content https://datasette.io/content

    Then:

        dclient query content 'select * from news limit 3'
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    aliases_file = config_dir / "aliases.json"
    aliases = _load_aliases(aliases_file)
    aliases[name] = url
    aliases_file.write_text(json.dumps(aliases, indent=4))


@alias.command(name="remove")
@click.argument("name")
def alias_remove(name):
    """
    Remove an alias

    Example usage:

    \b
        dclient alias remove content
    """
    config_dir = get_config_dir()
    aliases_file = config_dir / "aliases.json"
    aliases = _load_aliases(aliases_file)
    if name in aliases:
        del aliases[name]
        aliases_file.write_text(json.dumps(aliases, indent=4))
    else:
        raise click.ClickException("No such alias")


# --- auth commands ---


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
    for url, token in auths.items():
        click.echo("{}:\t{}..".format(url, token[:1]))


@auth.command(name="remove")
@click.argument("alias_or_url")
def auth_remove(alias_or_url):
    """
    Remove the API token for an alias or URL

    Example usage:

    \b
        dclient auth remove https://datasette.io/content
    """
    config_dir = get_config_dir()
    auth_file = config_dir / "auth.json"
    auths = _load_auths(auth_file)
    try:
        del auths[alias_or_url]
        auth_file.write_text(json.dumps(auths, indent=4))
    except KeyError:
        raise click.ClickException("No such URL or alias")


# --- Internal helpers ---


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
    *, url, table, batch, token, create, alter, pks, replace, ignore, verbose
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
        url = "{}/{}/-/insert".format(url, table)
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
        if "/json" in response.headers["content-type"]:
            data = response.json()
            if "errors" in data:
                raise click.ClickException("\n".join(data["errors"]))
        response.raise_for_status()
    response_data = response.json()
    if verbose:
        click.echo(textwrap.indent(json.dumps(response_data, indent=2), "  "), err=True)
    return response_data
