# Exploring data

dclient provides several commands for exploring Datasette instances without writing SQL.

## Listing databases

Use `dclient databases` to list all databases on a Datasette instance:

```bash
dclient databases https://latest.datasette.io
```

Use `--table` for a formatted text table:
```bash
dclient databases https://latest.datasette.io --table
```
Output:
```
name      path      is_mutable
--------  --------  ----------
fixtures  fixtures  False
```

## Listing tables

Use `dclient tables` to list tables in a specific database:

```bash
dclient tables https://latest.datasette.io/fixtures
```

Use `--table` for formatted output:
```bash
dclient tables https://latest.datasette.io/fixtures --table
```

Use `--schema` to include the CREATE TABLE SQL for each table:
```bash
dclient tables https://latest.datasette.io/fixtures --schema
```

Use `--views` to include views in the output (hidden by default).

## Viewing schemas

Use `dclient schema` to show the SQL schema for a database or an individual table:

```bash
# Schema for all tables in a database
dclient schema https://latest.datasette.io/fixtures

# Schema for a specific table
dclient schema https://latest.datasette.io/fixtures/facetable
```

## Browsing rows

Use `dclient rows` to browse table data with filtering, sorting, and pagination — no SQL required:

```bash
dclient rows https://latest.datasette.io/fixtures/facetable --table
```

### Filtering

Use `-w` / `--where` to filter rows. Supports [Datasette filter operators](https://docs.datasette.io/en/stable/json_api.html#table-arguments) like `__gt`, `__contains`, `__exact`, etc.:

```bash
# Exact match
dclient rows https://example.com/db/dogs -w breed=Poodle

# Greater than
dclient rows https://example.com/db/dogs -w age__gt=4

# Multiple filters (AND)
dclient rows https://example.com/db/dogs -w age__gte=3 -w breed=Labrador
```

For raw SQL WHERE clauses, use `--where-sql`:
```bash
dclient rows https://example.com/db/dogs --where-sql "age > 3 and breed != 'Poodle'"
```

### Sorting

```bash
# Sort ascending
dclient rows https://example.com/db/dogs --sort name

# Sort descending
dclient rows https://example.com/db/dogs --sort-desc age
```

### Selecting columns

```bash
# Include only specific columns
dclient rows https://example.com/db/dogs --col name --col breed

# Exclude specific columns
dclient rows https://example.com/db/dogs --nocol id
```

### Full-text search

```bash
dclient rows https://example.com/db/articles --search "python tutorial"
```

### Faceting

```bash
dclient rows https://example.com/db/dogs --facet breed
```
Facet results are printed to stderr, with the rows on stdout.

### Pagination

By default, only the first page of results is returned. Use `--all` to fetch every page:

```bash
dclient rows https://example.com/db/dogs --all
```

Control page size with `--size` and limit total rows with `--limit`:

```bash
# 10 rows per page, max 50 rows total
dclient rows https://example.com/db/dogs --size 10 --limit 50
```

## Fetching a single row

Use `dclient get` to fetch a single row by its primary key:

```bash
dclient get https://latest.datasette.io/fixtures/facetable 1
```
Output:
```json
{
  "pk": 1,
  "created": "2019-01-14 08:00:00",
  "planet_int": 1,
  "on_earth": 1,
  "state": "CA",
  ...
}
```

For compound primary keys, separate values with a comma:
```bash
dclient get https://example.com/db/compound_pk a,b
```

## Output formats

The `databases`, `tables`, `rows`, and `query` commands all support multiple output formats:

- `--json` — JSON (default)
- `--csv` — CSV
- `--tsv` — TSV
- `--nl` — Newline-delimited JSON
- `--table` — Formatted text table

```bash
dclient rows https://example.com/db/dogs --csv > dogs.csv
dclient rows https://example.com/db/dogs --table
```

## dclient databases --help
<!-- [[[cog
import cog
from dclient import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["databases", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient databases [OPTIONS] [URL_OR_ALIAS]

  List databases on a Datasette instance

  Example usage:

      dclient databases https://latest.datasette.io

Options:
  --token TEXT   API token
  -v, --verbose  Verbose output
  --csv          Output as CSV
  --tsv          Output as TSV
  --json         Output as JSON (default)
  --nl           Output as newline-delimited JSON
  --table        Output as text table
  --help         Show this message and exit.

```
<!-- [[[end]]] -->

## dclient tables --help
<!-- [[[cog
import cog
from dclient import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["tables", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient tables [OPTIONS] [URL_OR_ALIAS]

  List tables in a Datasette database

  Example usage:

      dclient tables https://latest.datasette.io/fixtures

Options:
  --token TEXT   API token
  --views        Include views
  --schema       Show CREATE TABLE SQL
  -v, --verbose  Verbose output
  --csv          Output as CSV
  --tsv          Output as TSV
  --json         Output as JSON (default)
  --nl           Output as newline-delimited JSON
  --table        Output as text table
  --help         Show this message and exit.

```
<!-- [[[end]]] -->

## dclient schema --help
<!-- [[[cog
import cog
from dclient import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["schema", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient schema [OPTIONS] [URL_OR_ALIAS]

  Show the SQL schema for a database or table

  Example usage:

      dclient schema https://latest.datasette.io/fixtures
      dclient schema https://latest.datasette.io/fixtures/facetable

Options:
  --token TEXT   API token
  -v, --verbose  Verbose output
  --help         Show this message and exit.

```
<!-- [[[end]]] -->

## dclient rows --help
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
Usage: dclient rows [OPTIONS] [URL_OR_ALIAS]

  Browse rows in a Datasette table with filtering and sorting

  Example usage:

      dclient rows https://latest.datasette.io/fixtures/facetable
      dclient rows https://latest.datasette.io/fixtures/facetable -w state=CA
      dclient rows https://latest.datasette.io/fixtures/facetable --sort city
      dclient rows https://latest.datasette.io/fixtures/facetable --search text

Options:
  --token TEXT      API token
  -w, --where TEXT  Filter: column__op=value (e.g. age__gt=30)
  --where-sql TEXT  Raw SQL WHERE clause
  --search TEXT     Full-text search query
  --sort TEXT       Sort by column (ascending)
  --sort-desc TEXT  Sort by column (descending)
  --col TEXT        Include only these columns
  --nocol TEXT      Exclude these columns
  --facet TEXT      Facet by column
  --size INTEGER    Number of rows per page
  --all             Fetch all pages
  --limit INTEGER   Maximum total rows to return
  -v, --verbose     Verbose output
  --csv             Output as CSV
  --tsv             Output as TSV
  --json            Output as JSON (default)
  --nl              Output as newline-delimited JSON
  --table           Output as text table
  --help            Show this message and exit.

```
<!-- [[[end]]] -->

## dclient get --help
<!-- [[[cog
import cog
from dclient import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["get", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient get [OPTIONS] [URL_OR_ALIAS] PK_VALUES

  Fetch a single row by primary key

  Example usage:

      dclient get https://latest.datasette.io/fixtures/facetable 1
      dclient get https://latest.datasette.io/fixtures/compound_pk a,b

Options:
  --token TEXT   API token
  -v, --verbose  Verbose output
  --help         Show this message and exit.

```
<!-- [[[end]]] -->
