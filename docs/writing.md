# Writing data

In addition to `insert` (documented in {doc}`inserting`), dclient provides several commands for modifying data in a Datasette instance via the [Write API](https://docs.datasette.io/en/latest/json_api.html#the-json-write-api).

All write commands require authentication. See {doc}`authentication` for how to set up tokens.

## Creating tables

Use `dclient create-table` to create a new empty table with an explicit schema:

```bash
dclient create-table https://example.com/db mytable \
  --column id integer \
  --column name text \
  --column age integer \
  --pk id
```
Output:
```json
{
  "ok": true,
  "database": "db",
  "table": "mytable",
  "schema": "CREATE TABLE [mytable] (\n   [id] INTEGER PRIMARY KEY,\n   [name] TEXT,\n   [age] INTEGER\n)"
}
```

Use `--pk` one or more times to set compound primary keys:
```bash
dclient create-table https://example.com/db events \
  --column date text --column venue text --column title text \
  --pk date --pk venue
```

## Upserting data

Use `dclient upsert` to insert rows or update existing ones based on primary key. This works like `insert` but uses the [upsert API endpoint](https://docs.datasette.io/en/latest/json_api.html#upserting-rows):

```bash
dclient upsert https://example.com/db mytable data.csv
```

The same file format options as `insert` are supported: `--csv`, `--tsv`, `--json`, `--nl`, `--encoding`, `--no-detect-types`.

Upsert from standard input:
```bash
echo '[{"id": 1, "name": "Updated"}]' | \
  dclient upsert https://example.com/db mytable - --json
```

Use `--alter` to add any missing columns automatically.

## Updating a single row

Use `dclient update` to update specific columns of a row by its primary key:

```bash
dclient update https://example.com/db/mytable 42 name=Alice age=30
```

Values are automatically parsed — numbers become integers/floats, `true`/`false` become booleans, `null` becomes null. Everything else is treated as a string.

Use `--alter` to allow adding new columns that don't exist yet.

## Deleting a row

Use `dclient delete` to delete a single row by primary key:

```bash
dclient delete https://example.com/db/mytable 42
```

You'll be prompted for confirmation. Use `--yes` to skip the prompt:
```bash
dclient delete https://example.com/db/mytable 42 --yes
```

## Dropping a table

Use `dclient drop` to drop an entire table:

```bash
dclient drop https://example.com/db/mytable
```

Without `--yes`, dclient will first query the table and show you the row count before asking for confirmation:
```
Drop table mytable (150 rows)? [y/N]:
```

Use `--yes` to skip confirmation:
```bash
dclient drop https://example.com/db/mytable --yes
```

## dclient create-table --help
<!-- [[[cog
import cog
from dclient import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["create-table", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient create-table [OPTIONS] URL_OR_ALIAS TABLE_NAME

  Create a new empty table with explicit schema

  Example usage:

      dclient create-table https://example.com/db mytable \
        --column id integer --column name text --pk id

Options:
  --column TEXT...  Column definition: name type (e.g. --column id integer
                    --column name text)
  --pk TEXT         Column(s) to use as primary key
  --token TEXT      API token
  -v, --verbose     Verbose output
  --help            Show this message and exit.

```
<!-- [[[end]]] -->

## dclient upsert --help
<!-- [[[cog
import cog
from dclient import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["upsert", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient upsert [OPTIONS] URL_OR_ALIAS TABLE FILEPATH

  Upsert data into a remote Datasette table

  Rows with matching primary keys will be updated; others will be inserted. Each
  row must include the primary key column(s).

  Example usage:

      dclient upsert \
        https://private.datasette.cloud/data \
        mytable data.csv

Options:
  --csv                 Input is CSV
  --tsv                 Input is TSV
  --json                Input is JSON
  --nl                  Input is newline-delimited JSON
  --encoding TEXT       Character encoding for CSV/TSV
  --no-detect-types     Don't detect column types for CSV/TSV
  --alter               Alter table to add any missing columns
  --batch-size INTEGER  Send rows in batches of this size
  --interval FLOAT      Send batch at least every X seconds
  -t, --token TEXT      API token
  --silent              Don't output progress
  -v, --verbose         Verbose output: show HTTP request and response
  --help                Show this message and exit.

```
<!-- [[[end]]] -->

## dclient update --help
<!-- [[[cog
import cog
from dclient import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["update", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient update [OPTIONS] URL_OR_ALIAS PK_VALUES [UPDATES]...

  Update a row by primary key

  Pass key=value pairs to set column values.

  Example usage:

      dclient update https://example.com/db/table 42 name=Alice age=30

Options:
  --token TEXT   API token
  --alter        Alter table to add any missing columns
  -v, --verbose  Verbose output
  --help         Show this message and exit.

```
<!-- [[[end]]] -->

## dclient delete --help
<!-- [[[cog
import cog
from dclient import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["delete", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient delete [OPTIONS] URL_OR_ALIAS PK_VALUES

  Delete a row by primary key

  Example usage:

      dclient delete https://example.com/db/table 42
      dclient delete https://example.com/db/table 42 --yes

Options:
  --token TEXT   API token
  --yes          Skip confirmation
  -v, --verbose  Verbose output
  --help         Show this message and exit.

```
<!-- [[[end]]] -->

## dclient drop --help
<!-- [[[cog
import cog
from dclient import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["drop", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient drop [OPTIONS] URL_OR_ALIAS

  Drop a table

  Example usage:

      dclient drop https://example.com/db/table
      dclient drop https://example.com/db/table --yes

Options:
  --token TEXT   API token
  --yes          Skip confirmation
  -v, --verbose  Verbose output
  --help         Show this message and exit.

```
<!-- [[[end]]] -->
