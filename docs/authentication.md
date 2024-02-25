(authentication)=

# Authentication

`dclient` can handle API tokens for Datasette instances that require authentication.

You can pass an API token to `query` using `-t/--token` like this:

```bash
dclient query https://latest.datasette.io/fixtures "select * from facetable" -t dstok_mytoken
```

A more convenient way to handle this is to store tokens to be used with different URL prefixes.

## Using stored tokens

To always use `dstok_mytoken` for any URL on the `https://latest.datasette.io/` instance you can run this:
```bash
dclient auth add https://latest.datasette.io/
```
Then paste in the token and hit enter when prompted to do so.

To list which URLs you have set tokens for, run the `auth list` command:
```bash
dclient auth list
```
To delete the token for a specific URL, run `auth remove`:
```bash
dclient auth remove https://latest.datasette.io/
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

      dclient auth add https://datasette.io/content

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

      dclient auth remove https://datasette.io/content

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->
