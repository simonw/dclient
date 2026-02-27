# Running queries

You can run SQL queries against a Datasette instance like this:

```bash
dclient query fixtures "select * from facetable limit 1" -i https://latest.datasette.io
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

The `query` command takes a database name and SQL string as positional arguments. Use `-i` to specify the instance (alias or URL). If you have a default instance and default database configured, you can use the bare SQL shortcut instead:

```bash
dclient "select * from facetable limit 1"
```

You can override just the database with `-d`:

```bash
dclient "select * from counters" -d counters
```

## Output formats

By default, results are returned as JSON. Use these flags to change the output format:

- `--csv` — CSV
- `--tsv` — TSV
- `-t` / `--table` — ASCII table
- `--nl` — newline-delimited JSON (one JSON object per line)

These flags work with both `dclient query` and the bare SQL shortcut.

CSV output:

```bash
dclient query fixtures "select * from facetable limit 2" -i latest --csv
```
```
pk,created,planet_int,on_earth,state,_city_id,_neighborhood
1,2019-01-14 08:00:00,1,1,CA,1,Mission
2,2019-01-15 08:00:00,1,1,CA,1,Dogpatch
```

ASCII table output:

```bash
dclient query fixtures "select pk, state, _neighborhood from facetable limit 3" -i latest -t
```
```
pk  state  _neighborhood
--  -----  -------------
1   CA     Mission
2   CA     Dogpatch
3   CA     SOMA
```

Newline-delimited JSON, useful for piping into `jq` or other line-oriented tools:

```bash
dclient query fixtures "select pk, state from facetable limit 2" -i latest --nl
```
```
{"pk": 1, "state": "CA"}
{"pk": 2, "state": "CA"}
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
Usage: dclient query [OPTIONS] DATABASE SQL

  Run a SQL query against a Datasette database

  Requires both a database name and a SQL string.

  Example usage:

      dclient query fixtures "select * from facetable limit 5"
      dclient query analytics "select count(*) from events" -i staging

Options:
  -i, --instance TEXT  Datasette instance URL or alias
  --token TEXT         API token
  -v, --verbose        Verbose output: show HTTP request
  --csv                Output as CSV
  --tsv                Output as TSV
  --nl                 Output as newline-delimited JSON
  -t, --table          Output as ASCII table
  --help               Show this message and exit.

```
<!-- [[[end]]] -->
