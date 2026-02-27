(authentication)=

# Authentication

`dclient` can handle API tokens for Datasette instances that require authentication.

You can pass an API token to any command using `--token` like this:

```bash
dclient query fixtures "select * from facetable" --token dstok_mytoken -i latest
```

A more convenient way to handle this is to store tokens for your aliases.

## Logging in with OAuth

The easiest way to authenticate is using the `dclient login` command, which uses the OAuth device flow to obtain and store a token.

This requires the Datasette instance to be running the [datasette-oauth](https://github.com/datasette/datasette-oauth) plugin with [device flow enabled](https://github.com/datasette/datasette-oauth?tab=readme-ov-file#plugin-configuration).

```bash
dclient login https://my-datasette.example.com/
dclient login myalias
dclient login
```

This will display a URL and a code. Open the URL in your browser, enter the code to approve access, and the resulting API token will be saved automatically. If you run `dclient login` without an argument, you will be prompted for the instance URL or alias.

### Requesting scoped tokens

By default, `dclient login` requests an unrestricted token. You can request a token with limited permissions using the shorthand options:

```bash
# Instance-wide read or write access
dclient login --read-all
dclient login --write-all

# Database-level access
dclient login --read db1
dclient login --write db3

# Table-level access
dclient login --read db1/dogs
dclient login --write db3/submissions

# Mixed
dclient login --read db1 --write db3/dogs
```

`--read-all` grants: `view-instance`, `view-table`, `view-database`, `view-query`, `execute-sql`.

`--write-all` grants all read scopes plus: `insert-row`, `delete-row`, `update-row`, `create-table`, `alter-table`, `drop-table`.

`--read` and `--write` accept a database name or `database/table` and can be specified multiple times. `--write` implies read access for the same target.

For advanced use, you can also pass raw scope JSON with `--scope`:

```bash
dclient login myalias --scope '[["view-instance"]]'
```

All scope options can be combined — the shorthand options append to whatever `--scope` provides.

### Outputting the token directly

Use `--token-only` to print the token to stdout instead of saving it. This is useful for creating debug tokens or piping them into other tools:

```bash
dclient login --token-only --read mydb
dclient login --token-only --write-all
```

## dclient login --help

<!-- [[[cog
import cog
from dclient import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["login", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient login [OPTIONS] [ALIAS_OR_URL]

  Authenticate with a Datasette instance using OAuth

  Uses the OAuth device flow: opens a URL in your browser where you approve
  access, then saves the resulting API token.

  Example usage:

      dclient login https://simon.datasette.cloud/
      dclient login myalias
      dclient login
      dclient login --read-all
      dclient login --write-all
      dclient login --read db1
      dclient login --write db3/submissions
      dclient login --read db1 --write db3/dogs

Options:
  --scope TEXT  JSON scope array
  --read-all    Request instance-wide read access
  --write-all   Request instance-wide write access
  --read TEXT   Request read access for a database or database/table
  --write TEXT  Request write access for a database or database/table
  --token-only  Output the token to stdout instead of saving it
  --help        Show this message and exit.

```
<!-- [[[end]]] -->

## Using stored tokens

To store a token for an alias:
```bash
dclient auth add latest
```
Then paste in the token and hit enter when prompted to do so.

Tokens can also be stored for direct URLs:
```bash
dclient auth add https://latest.datasette.io
```

To list which aliases/URLs you have set tokens for, run the `auth list` command:
```bash
dclient auth list
```
To delete the token for a specific alias or URL, run `auth remove`:
```bash
dclient auth remove latest
```

## Token resolution order

When making a request, dclient resolves the token in this order:

1. `--token` CLI flag (highest priority)
2. Token stored by alias name in `auth.json`
3. Token stored by URL prefix in `auth.json`
4. `DATASETTE_TOKEN` environment variable (lowest priority)

## Testing a token

The `dclient auth status` command can be used to verify authentication by calling `/-/actor.json`:
```bash
dclient auth status
dclient auth status -i prod
```

The `dclient actor` command also shows the actor:
```bash
dclient actor
dclient actor -i prod
```
The output looks like this:
```json
{
    "actor": {
        "id": "root",
        "token": "dstok"
    }
}
```

## dclient auth --help
<!-- [[[cog
import cog
from dclient import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["auth", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient auth [OPTIONS] COMMAND [ARGS]...

  Manage authentication for different instances

Options:
  --help  Show this message and exit.

Commands:
  add     Add an authentication token for an alias or URL
  list    List stored API tokens
  remove  Remove the API token for an alias or URL
  status  Verify authentication by calling /-/actor.json

```
<!-- [[[end]]] -->

## dclient auth add --help

<!-- [[[cog
import cog
result = runner.invoke(cli.cli, ["auth", "add", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient auth add [OPTIONS] ALIAS_OR_URL

  Add an authentication token for an alias or URL

  Example usage:

      dclient auth add prod
      dclient auth add https://datasette.io

  Paste in the token when prompted.

Options:
  --token TEXT
  --help        Show this message and exit.

```
<!-- [[[end]]] -->

## dclient auth list --help

<!-- [[[cog
import cog
result = runner.invoke(cli.cli, ["auth", "list", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient auth list [OPTIONS]

  List stored API tokens

  Example usage:

      dclient auth list

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

## dclient auth remove --help

<!-- [[[cog
import cog
result = runner.invoke(cli.cli, ["auth", "remove", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient auth remove [OPTIONS] ALIAS_OR_URL

  Remove the API token for an alias or URL

  Example usage:

      dclient auth remove prod

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

## dclient auth status --help

<!-- [[[cog
import cog
result = runner.invoke(cli.cli, ["auth", "status", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient auth status [OPTIONS]

  Verify authentication by calling /-/actor.json

  Example usage:

      dclient auth status
      dclient auth status -i prod

Options:
  -i, --instance TEXT  Datasette instance URL or alias
  --token TEXT         API token
  --help               Show this message and exit.

```
<!-- [[[end]]] -->

## dclient actor --help

<!-- [[[cog
import cog
result = runner.invoke(cli.cli, ["actor", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient actor [OPTIONS]

  Show the actor represented by an API token

  Example usage:

      dclient actor
      dclient actor -i prod

Options:
  -i, --instance TEXT  Datasette instance URL or alias
  --token TEXT         API token
  --help               Show this message and exit.

```
<!-- [[[end]]] -->
