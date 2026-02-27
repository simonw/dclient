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

## Browsing rows

The `dclient rows` command lets you browse table data without writing SQL:

```bash
dclient rows fixtures facet_cities -i https://latest.datasette.io -t
```
```
id  name
--  -------------
3   Detroit
2   Los Angeles
4   Memnonia
1   San Francisco
```

If you have a default instance and database configured, you can just pass the table name:

```bash
dclient rows facet_cities -t
```

### Filtering

Use `-f` / `--filter` with three arguments: column, operation, value:

```bash
dclient rows facet_cities -f id gte 3 -t
dclient rows facet_cities -f name eq Detroit
dclient rows facet_cities -f name contains M -f id gt 2
```

The operation is passed directly to Datasette as a column filter suffix. Built-in Datasette operations include `exact`, `not`, `gt`, `gte`, `lt`, `lte`, `contains`, `like`, `startswith`, `endswith`, `glob`, `isnull`, `notnull`, and more. `eq` is a convenience alias for `exact`. Operations added by Datasette plugins will work too.

### Sorting

```bash
dclient rows dogs --sort age
dclient rows dogs --sort-desc age
```

### Column selection

```bash
dclient rows dogs --col name --col age
dclient rows dogs --nocol id
```

### Search

Full-text search (requires an FTS index on the table):

```bash
dclient rows dogs --search "retriever"
```

### Pagination

By default only one page of results is returned. Use `--all` to auto-paginate through all rows, and `--limit` to cap the total:

```bash
dclient rows dogs --all
dclient rows dogs --all --limit 500
dclient rows dogs --size 50
```

### dclient rows --help
<!-- [[[cog
import cog
from dclient import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["rows", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient rows [OPTIONS] DB_OR_TABLE [TABLE]

  Browse rows in a table with filtering and sorting

  If only one positional argument is given, it is treated as the table name and
  the default database is used. Pass two arguments for database and table.

  Example usage:

      dclient rows facet_cities
      dclient rows fixtures facet_cities -i https://latest.datasette.io
      dclient rows facet_cities -f id gte 3 --sort name -t

Options:
  -i, --instance TEXT   Datasette instance URL or alias
  -d, --database TEXT   Database name
  --token TEXT          API token
  -f, --filter TEXT...  Filter: column operation value (e.g. -f age gte 3)
  --search TEXT         Full-text search query
  --sort TEXT           Sort by column (ascending)
  --sort-desc TEXT      Sort by column (descending)
  --col TEXT            Include only these columns
  --nocol TEXT          Exclude these columns
  --size INTEGER        Number of rows per page
  --limit INTEGER       Maximum total rows to return
  --all                 Fetch all pages
  -v, --verbose         Verbose output: show HTTP request
  --csv                 Output as CSV
  --tsv                 Output as TSV
  --nl                  Output as newline-delimited JSON
  -t, --table           Output as ASCII table
  --help                Show this message and exit.

```
<!-- [[[end]]] -->

## Output formats

By default, results are returned as JSON. Use these flags to change the output format:

- `--csv` — CSV
- `--tsv` — TSV
- `-t` / `--table` — ASCII table
- `--nl` — newline-delimited JSON (one JSON object per line)

These flags work with `dclient query`, `dclient rows`, and the bare SQL shortcut.

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
