(environment-variables)=

# Environment variables

`dclient` supports several environment variables for convenient access to Datasette instances.

## DATASETTE_URL

Set this to the base URL of your Datasette instance. It is used as a fallback when no instance is specified via `-i` and no default instance is configured:

```bash
export DATASETTE_URL=https://my-instance.datasette.cloud
```

Then you can omit the `-i` flag:

```bash
dclient databases
dclient query data "select * from my_table limit 10"
```

Aliases and the `-i` flag always take priority over `DATASETTE_URL`.

## DATASETTE_DATABASE

Set this to a default database name. It is used as a fallback when no database is specified via `-d` and the current instance has no `default_database` configured:

```bash
export DATASETTE_DATABASE=data
```

Then you can use the bare SQL shortcut:

```bash
dclient "select * from my_table limit 10"
```

## DATASETTE_TOKEN

Set this to an API token:

```bash
export DATASETTE_TOKEN=dstok_abc123
```

The token will be used automatically for any request that doesn't have a more specific token configured.

The precedence order for tokens is:

1. `--token` CLI flag (highest priority)
2. Stored token from `auth.json` (matched by alias name, then URL prefix)
3. `DATASETTE_TOKEN` environment variable (lowest priority)

## DCLIENT_CONFIG_DIR

Override the config directory (default `~/.config/io.datasette.dclient` or platform equivalent):

```bash
export DCLIENT_CONFIG_DIR=/path/to/config
```

This is useful for testing or running multiple configurations side by side.

## Using them together

These variables work well together for quick access to a single instance:

```bash
export DATASETTE_URL=https://my-instance.datasette.cloud
export DATASETTE_DATABASE=data
export DATASETTE_TOKEN=dstok_abc123

# Query
dclient "select * from my_table"

# Insert
cat records.json | dclient insert data my_table - --json

# Check your actor identity
dclient actor
```
