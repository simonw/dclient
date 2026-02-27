# Aliases

You can assign an alias to a Datasette instance using the `dclient alias add` command:

    dclient alias add latest https://latest.datasette.io

You can list aliases with `dclient alias list`:

    $ dclient alias list
      latest = https://latest.datasette.io

Once registered, you can pass an alias to commands using the `-i` flag:

    dclient query fixtures "select * from news limit 1" -i latest

See [Defaults](defaults.md) for default instance and default database settings.

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
  add     Add an alias for a Datasette instance
  list    List aliases
  remove  Remove an alias

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
