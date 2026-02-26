(authentication)=

# Authentication

`dclient` can handle API tokens for Datasette instances that require authentication.

You can pass an API token to any command using `--token` like this:

```bash
dclient query fixtures "select * from facetable" --token dstok_mytoken -i latest
```

A more convenient way to handle this is to store tokens for your aliases.

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
