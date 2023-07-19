# Inserting data

The `dclient insert` command can be used to insert data from a local file directly into a Datasette instance, via the [Write API](https://docs.datasette.io/en/latest/json_api.html#the-json-write-api) introduced in the Datasette 1.0 alphas.

First you'll need to {ref}`authenticate <authentication>` with the instance.

To insert data from a `data.csv` file into a table called `my_table`, creating that table if it does not exist:

```bash
dclient insert https://my-private-space.datasette.cloud/data my_table data.csv --create
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
- `--pk id` - set a primary key (for if the table is being created)

If you use `--create` a table will be created with rows to match the columns in your uploaded data - using the correctly detected types, unless you use `--no-detect-types` in which case every column will be of type `text`.
