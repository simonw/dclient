(environment-variables)=

# Environment variables

`dclient` supports two environment variables for convenient access to a Datasette instance without needing aliases or repeated URLs.

## DATASETTE_URL

Set this to the base URL of your Datasette instance:

```bash
export DATASETTE_URL=https://my-instance.datasette.cloud
```

Then pass just the database name as the first argument to any command:

```bash
dclient query data "select * from my_table limit 10"
```

This is equivalent to:

```bash
dclient query https://my-instance.datasette.cloud/data "select * from my_table limit 10"
```

It works with all commands:

```bash
dclient insert data my_table data.csv --csv
dclient actor data
```

Full URLs and aliases always take priority over `DATASETTE_URL`. If the argument starts with `http://` or `https://`, it is used as-is. If it matches an alias in `aliases.json`, the alias is used.

## DATASETTE_TOKEN

Set this to an API token:

```bash
export DATASETTE_TOKEN=dstok_abc123
```

The token will be used automatically for any request that doesn't have a more specific token configured.

The precedence order for tokens is:

1. `--token` CLI flag (highest priority)
2. Stored token from `auth.json` (matched by URL prefix)
3. `DATASETTE_TOKEN` environment variable (lowest priority)

## Using both together

These variables work well together for quick access to a single instance:

```bash
export DATASETTE_URL=https://my-instance.datasette.cloud
export DATASETTE_TOKEN=dstok_abc123

# Query the "data" database
dclient query data "select * from my_table"

# Insert into the "data" database
cat records.json | dclient insert data my_table - --json

# Check your actor identity
dclient actor data
```
