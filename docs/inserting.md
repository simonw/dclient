# Inserting data

The `dclient insert` command can be used to insert data from a local file directly into a Datasette instance, via the [Write API](https://docs.datasette.io/en/latest/json_api.html#the-json-write-api) introduced in the Datasette 1.0 alphas.

First you'll need to {ref}`authenticate <authentication>` with the instance.

To insert data from a `data.csv` file into a table called `my_table`, creating that table if it does not exist:

```bash
dclient insert \
  https://my-private-space.datasette.cloud/data \
  my_table data.csv --create
```
You can also pipe data into standard input:
```bash
curl -s 'https://api.github.com/repos/simonw/dclient/issues' | \
  dclient insert \
    https://my-private-space.datasette.cloud/data \
    issues - --create
```

## Streaming data

`dclient insert` works for streaming data as well.

If you have a log file containing newline-delimited JSON you can tail it and send it to a Datasette instance like this:
```bash
tail -f log.jsonl | \
  dclient insert https://my-private-space.datasette.cloud/data logs - --nl
```
When reading from standard input (filename `-`) you are required to specify the format. In this example that's `--nl` for newline-delimited JSON. `--csv` and `--tsv` are supported for streaming as well, but `--json` is not.

In streaming mode records default to being sent to the server every 100 records or every 10 seconds, whichever comes first. You can adjust these values using the `--batch-size` and `--interval` settings. For example, here's how to send every 10 records or if 5 seconds has passed since the last time data was sent to the server:

```bash
tail -f log.jsonl | dclient insert \
  https://my-private-space.datasette.cloud/data logs - --nl --create \
  --batch-size 10 \
  --interval 5
```

## Supported formats

Data can be inserted from CSV, TSV, JSON or newline-delimited JSON files.

The format of the file will be automatically detected. You can override this by using one of the following options:

- `--csv`
- `--tsv`
- `--json`
- `--nl` for newline-delimited JSON

Use `--encoding <encoding>` to specify the encoding of the file. The default is `utf-8`.

### JSON

JSON files should be formatted like this:
```json
[
    {
        "id": 1
        "column1": "value1",
        "column2": "value2"
    },
    {
        "id": 2
        "column1": "value1",
        "column2": "value2"
    }
]
```
Newline-delimited files like this:
```
{"id": 1, "column1": "value1", "column2": "value2"}
{"id": 2, "column1": "value1", "column2": "value2"}
```

### CSV and TSV

CSV and TSV files should have a header row containing the names of the columns.

By default, `dclient` will attempt to detect the types of the different columns in the CSV and TSV files - so if a column only ever contains numeric integers it will be stored as integers in the SQLite database.

You can disable this and have every value treated as a string using `--no-detect-types`.

### Other options

- `--create` - create the table if it doesn't already exist
- `--replace` - replace any rows with a matching primary key
- `--ignore` - ignore any rows with a matching existing primary key
- `--alter` - alter table to add any columns that are missing
- `--pk id` - set a primary key (for if the table is being created)

If you use `--create` a table will be created with rows to match the columns in your uploaded data - using the correctly detected types, unless you use `--no-detect-types` in which case every column will be of type `text`.

## dclient insert --help
<!-- [[[cog
import cog
from dclient import cli
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli.cli, ["insert", "--help"])
help = result.output.replace("Usage: cli", "Usage: dclient")
cog.out(
    "```\n{}\n```".format(help)
)
]]] -->
```
Usage: dclient insert [OPTIONS] URL_OR_ALIAS TABLE FILEPATH

  Insert data into a remote Datasette instance

  Example usage:

      dclient insert \
        https://private.datasette.cloud/data \
        mytable data.csv --pk id --create

Options:
  --csv                 Input is CSV
  --tsv                 Input is TSV
  --json                Input is JSON
  --nl                  Input is newline-delimited JSON
  --encoding TEXT       Character encoding for CSV/TSV
  --no-detect-types     Don't detect column types for CSV/TSV
  --replace             Replace rows with a matching primary key
  --ignore              Ignore rows with a matching primary key
  --create              Create table if it does not exist
  --alter               Alter table to add any missing columns
  --pk TEXT             Columns to use as the primary key when creating the
                        table
  --batch-size INTEGER  Send rows in batches of this size
  --interval FLOAT      Send batch at least every X seconds
  -t, --token TEXT      API token
  --silent              Don't output progress
  --help                Show this message and exit.

```
<!-- [[[end]]] -->
