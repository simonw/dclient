# Aliases

You can assign an alias to a Datasette database using the `dclient alias` command:

    dclient alias add content https://datasette.io/content

You can list aliases with `dclient alias list`:

    $ dclient alias list
    content = https://datasette.io/content

Once registered, you can pass an alias to commands such as `dclient query`:

    dclient query content "select * from news limit 1"

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
  add     Add an alias
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

  Add an alias

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

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->
