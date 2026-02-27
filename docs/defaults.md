# Defaults

Set a default instance so you don't need `-i` every time:

    dclient default instance latest

Now commands will use `latest` automatically:

    dclient databases
    dclient tables -d fixtures

Set a default database for an alias or instance URL:

    dclient default database latest fixtures
    dclient default database https://latest.datasette.io fixtures

Now you can run bare SQL queries directly:

    dclient "select * from facetable limit 5"

This uses the default instance and default database.

## dclient default --help
<!-- [[[cog
import cog
from dclient import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["default", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient default [OPTIONS] COMMAND [ARGS]...

  Manage default instance and database

Options:
  --help  Show this message and exit.

Commands:
  database  Set or show the default database for an instance
  instance  Set or show the default instance

```
<!-- [[[end]]] -->

## dclient default instance --help

<!-- [[[cog
import cog
result = runner.invoke(cli.cli, ["default", "instance", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient default instance [OPTIONS] [ALIAS_OR_URL]

  Set or show the default instance

  Example usage:

      dclient default instance prod
      dclient default instance https://myapp.datasette.cloud
      dclient default instance
      dclient default instance --clear

Options:
  --clear  Clear default instance
  --help   Show this message and exit.

```
<!-- [[[end]]] -->

## dclient default database --help

<!-- [[[cog
import cog
result = runner.invoke(cli.cli, ["default", "database", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient default database [OPTIONS] ALIAS_OR_URL [DB]

  Set or show the default database for an instance

  Example usage:

      dclient default database prod main
      dclient default database https://myapp.datasette.cloud main
      dclient default database prod
      dclient default database prod --clear

Options:
  --clear  Clear default database for this instance
  --help   Show this message and exit.

```
<!-- [[[end]]] -->
