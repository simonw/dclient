import click
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
    return pathlib.Path(click.get_app_dir("io.datasette.dclient"))


@click.group()
@click.version_option()
def cli():
    "A client CLI utility for Datasette instances"


@cli.command()
@click.argument("url_or_alias")
@click.argument("sql")
@click.option("--token", help="API token")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output: show HTTP request")
def query(url_or_alias, sql, token, verbose):
    """
    Run a SQL query against a Datasette database URL

    Returns a JSON array of objects

    Example usage:

    \b
        dclient query \\
          https://datasette.io/content \\
          'select * from news limit 10'
    """
    url = _resolve_url(url_or_alias)
    token = _resolve_token(token, url)
    if not url.endswith(".json"):
        url += ".json"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    params = {"sql": sql, "_shape": "objects"}
    if verbose:
        click.echo(url + "?" + urllib.parse.urlencode(params), err=True)
    response = httpx.get(url, params=params, headers=headers, follow_redirects=True)

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
    token = _resolve_token(token, url)

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
        # Disable progress bar - it can't handle these formats
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
                    # File has likely been closed, so fp.tell() fails
                    pass
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


@cli.command()
@click.argument("url_or_alias")
@click.option("--token", help="API token")
def actor(url_or_alias, token):
    """
    Show the actor represented by an API token

    Example usage:

    \b
        dclient actor https://latest.datasette.io/fixtures
    """
    url = _resolve_url(url_or_alias)

    if not (url.startswith("http://") or url.startswith("https://")):
        raise click.ClickException("Invalid URL: " + url)

    token = _resolve_token(token, url)

    url_bits = url.split("/")
    url_bits[-1] = "-/actor.json"
    actor_url = "/".join(url_bits)
    response = httpx.get(
        actor_url, headers={"Authorization": "Bearer {}".format(token)}, timeout=40.0
    )
    response.raise_for_status()
    click.echo(json.dumps(response.json(), indent=4))


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


@auth.command(name="login")
@click.argument("url_or_alias")
@click.option("--scope", "scope_json", default=None, help="JSON array of scope arrays")
@click.option("--open/--no-open", "open_browser", default=True, help="Open browser automatically")
def auth_login(url_or_alias, scope_json, open_browser):
    """
    Log in to a Datasette instance using the device authorization flow

    Example usage:

    \b
        dclient auth login https://my-datasette.example.com/data

    This will display a code and URL. Visit the URL in your browser,
    sign in to Datasette, and enter the code to authorize this device.
    """
    import webbrowser

    url = _resolve_url(url_or_alias)

    # Find the base Datasette URL (strip database/table path)
    # We need the root URL for the OAuth endpoints
    base_url = url.rstrip("/")

    # POST to the device endpoint
    data = {}
    if scope_json:
        data["scope"] = scope_json

    try:
        response = httpx.post(
            f"{base_url}/-/oauth/device",
            data=data,
            timeout=30.0,
        )
    except httpx.ConnectError:
        raise click.ClickException(f"Could not connect to {base_url}")

    if response.status_code != 200:
        try:
            error = response.json().get("error", response.text)
        except Exception:
            error = response.text
        raise click.ClickException(f"Device authorization failed: {error}")

    device_data = response.json()
    device_code = device_data["device_code"]
    user_code = device_data["user_code"]
    verification_uri = device_data["verification_uri"]
    interval = device_data.get("interval", 5)
    expires_in = device_data.get("expires_in", 900)

    click.echo(f"Enter this code in your browser: {user_code}")
    click.echo()
    click.echo(f"  {verification_uri}?code={user_code}")
    click.echo()

    if open_browser:
        webbrowser.open(f"{verification_uri}?code={user_code}")
        click.echo("Browser opened. Waiting for authorization...")
    else:
        click.echo("Waiting for authorization...")

    # Poll for the token
    deadline = time.time() + expires_in
    while time.time() < deadline:
        time.sleep(interval)

        token_response = httpx.post(
            f"{base_url}/-/oauth/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
            },
            timeout=30.0,
        )

        token_data = token_response.json()

        if token_response.status_code == 200 and "access_token" in token_data:
            # Store the token
            access_token = token_data["access_token"]
            config_dir = get_config_dir()
            config_dir.mkdir(parents=True, exist_ok=True)
            auth_file = config_dir / "auth.json"
            auths = _load_auths(auth_file)
            auths[url] = access_token
            auth_file.write_text(json.dumps(auths, indent=4))

            click.echo(f"Authenticated! Token saved for {url}")
            return

        error = token_data.get("error", "")
        if error == "authorization_pending":
            continue
        elif error == "slow_down":
            interval += 5
            continue
        elif error == "access_denied":
            raise click.ClickException("Authorization was denied")
        elif error == "expired_token":
            raise click.ClickException("Device code expired. Please try again.")
        else:
            raise click.ClickException(f"Token exchange failed: {error}")

    raise click.ClickException("Timed out waiting for authorization")


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
    aliases = _load_aliases(get_config_dir() / "aliases.json")
    if url_or_alias in aliases:
        return aliases[url_or_alias]
    if url_or_alias.startswith("http://") or url_or_alias.startswith("https://"):
        return url_or_alias
    base_url = os.environ.get("DATASETTE_URL")
    if base_url:
        return base_url.rstrip("/") + "/" + url_or_alias
    return url_or_alias


def _resolve_token(token, url):
    if token is not None:
        return token
    stored = token_for_url(url, _load_auths(get_config_dir() / "auth.json"))
    if stored is not None:
        return stored
    return os.environ.get("DATASETTE_TOKEN")


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
