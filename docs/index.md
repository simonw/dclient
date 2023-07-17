# dclient

[![PyPI](https://img.shields.io/pypi/v/dclient.svg)](https://pypi.org/project/dclient/)
[![Changelog](https://img.shields.io/github/v/release/simonw/dclient?include_prereleases&label=changelog)](https://github.com/simonw/dclient/releases)
[![Tests](https://github.com/simonw/dclient/workflows/Test/badge.svg)](https://github.com/simonw/dclient/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/dclient/blob/master/LICENSE)

A client CLI utility for [Datasette](https://datasette.io/) instances

## Installation

Install `dclient` using `pip` (or [pipx](https://pipxproject.github.io/pipx/):

```bash
pip install dclient
```

### As a Datasette plugin

If you also have Datasette installed in the same environment it will register itself as a command plugin.

This means you can run any of these commands using `datasette client` instead, like this:
```bash
datasette client --help
datasette client query https://latest.datasette.io/fixtures "select * from facetable limit 1"
```
You can install it into Datasette this way using:

```bash
datasette install dclient
```
## Running queries

You can run SQL queries against a Datasette instance like this:

```bash
dclient query https://latest.datasette.io/fixtures "select * from facetable limit 1"
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
  -t, --token TEXT  API token
  --help            Show this message and exit.

```
<!-- [[[end]]] -->


## Contents

```{toctree}
---
maxdepth: 3
---
aliases
authentication
```
