# dclient

[![PyPI](https://img.shields.io/pypi/v/dclient.svg)](https://pypi.org/project/dclient/)
[![Changelog](https://img.shields.io/github/v/release/simonw/dclient?include_prereleases&label=changelog)](https://github.com/simonw/dclient/releases)
[![Tests](https://github.com/simonw/dclient/workflows/Test/badge.svg)](https://github.com/simonw/dclient/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/dclient/blob/master/LICENSE)

A client CLI utility for [Datasette](https://datasette.io/) instances

## Installation

Install this tool using `pip`:

    pip install dclient

If you want to install it in the same virtual environment as Datasette (to use it as a plugin) you can instead run:

    datasette install dclient

## Standalone v.s. plugin

Once installed you can use this tool like so:

    dclient --help

If you also have Datasette installed in the same environment it will register itself as a command plugin.

This means you can run any of these commands using `datasette client` instead, like this:

    datasette client --help
    datasette client query https://latest.datasette.io/fixtures "select * from facetable limit 1"

## Running queries

You can run SQL queries against a Datasette instance like this:

```
$ dclient query https://latest.datasette.io/fixtures "select * from facetable limit 1"
```
Output:
```json
[
  {
    "pk": 1,
    "created": "2019-01-14 08:00:00",
    "planet_int": 1,
    "on_earth": 1,
    "state": "CA",
    "_city_id": 1,
    "_neighborhood": "Mission",
    "tags": "[\"tag1\", \"tag2\"]",
    "complex_array": "[{\"foo\": \"bar\"}]",
    "distinct_some_null": "one",
    "n": "n1"
  }
]
```

### dclient query --help
<!-- [[[cog
import cog
from dclient import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["query", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient query [OPTIONS] URL SQL

  Run a SQL query against a Datasette database URL

  Returns a JSON array of objects

Options:
  --help  Show this message and exit.

```
<!-- [[[end]]] -->

## Aliases

You can assign an alias to a Datasette database using the `dclient alias` command:

    dclient alias add content https://datasette.io/content

You can list aliases with `dclient alias list`:

    $ dclient alias list
    content = https://datasette.io/content

Once registered, you can pass an alias to commands such as `dclient query`:

    dclient query content "select * from news limit 1"

### dclient alias --help

<!-- [[[cog
import cog
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

### dclient alias list --help

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

### dclient alias add --help

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

### dclient alias remove --help

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

## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment:

    cd dclient
    python -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
