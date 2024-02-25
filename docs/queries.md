# Running queries

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

## dclient query --help
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
Usage: dclient query [OPTIONS] URL_OR_ALIAS SQL

  Run a SQL query against a Datasette database URL

  Returns a JSON array of objects

  Example usage:

      dclient query \
        https://datasette.io/content \
        'select * from news limit 10'

Options:
  --token TEXT  API token
  --help        Show this message and exit.

```
<!-- [[[end]]] -->
