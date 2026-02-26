# Aliases

You can assign an alias to a Datasette instance using the `dclient alias add` command:

    dclient alias add latest https://latest.datasette.io

You can list aliases with `dclient alias list`:

    $ dclient alias list
      latest = https://latest.datasette.io

Once registered, you can pass an alias to commands using the `-i` flag:

    dclient query fixtures "select * from news limit 1" -i latest

## Default instance

Set a default instance so you don't need `-i` every time:

    dclient alias default latest

Now commands will use `latest` automatically:

    dclient databases
    dclient tables -d fixtures

## Default database

Set a default database for an alias:

    dclient alias default-db latest fixtures

Now you can run bare SQL queries directly:

    dclient "select * from facetable limit 5"

This uses the default instance and default database.

## dclient alias --help
<!-- [[[cog
import cog
from dclient import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["alias", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient alias [OPTIONS] COMMAND [ARGS]...

  Manage aliases for different instances

Options:
  --help  Show this message and exit.

Commands:
  add         Add an alias for a Datasette instance
  default     Set or show the default instance
  default-db  Set or show the default database for an alias
  list        List aliases
  remove      Remove an alias

```
<!-- [[[end]]] -->

## dclient alias list --help

<!-- [[[cog
import cog
result = runner.invoke(cli.cli, ["alias", "list", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient alias list [OPTIONS]

  List aliases

Options:
  --json  Output raw JSON
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

## dclient alias add --help

<!-- [[[cog
import cog
result = runner.invoke(cli.cli, ["alias", "add", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient alias add [OPTIONS] NAME URL

  Add an alias for a Datasette instance

  Example usage:

      dclient alias add prod https://myapp.datasette.cloud

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

## dclient alias remove --help

<!-- [[[cog
import cog
result = runner.invoke(cli.cli, ["alias", "remove", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient alias remove [OPTIONS] NAME

  Remove an alias

  Example usage:

      dclient alias remove prod

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

## dclient alias default --help

<!-- [[[cog
import cog
result = runner.invoke(cli.cli, ["alias", "default", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient alias default [OPTIONS] [NAME]

  Set or show the default instance

  Example usage:

      dclient alias default prod
      dclient alias default
      dclient alias default --clear

Options:
  --clear  Clear default instance
  --help   Show this message and exit.

```
<!-- [[[end]]] -->

## dclient alias default-db --help

<!-- [[[cog
import cog
result = runner.invoke(cli.cli, ["alias", "default-db", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient alias default-db [OPTIONS] ALIAS_NAME [DB]

  Set or show the default database for an alias

  Example usage:

      dclient alias default-db prod main
      dclient alias default-db prod
      dclient alias default-db prod --clear

Options:
  --clear  Clear default database for this alias
  --help   Show this message and exit.

```
<!-- [[[end]]] -->
