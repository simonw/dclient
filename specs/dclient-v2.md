# dclient v2 — Changes from v1

## Summary of changes

1. Aliases point at Datasette instances, not database URLs
2. Instance is always a flag (`-i`/`--instance`), never a positional argument
3. `query` and `insert`/`upsert` take database as a required positional argument
4. Introspection commands (`tables`, `schema`, etc.) use `-d`/`--database` with defaults
5. Default instance and default database reduce typing
6. Bare SQL defaults to `query` command via `click-default-group`, using defaults + `-d` override
7. New commands: `databases`, `tables`, `schema`, `plugins`
8. Config and auth remain separate files, with a new config format
9. New `DATASETTE_DATABASE` environment variable

---

## Config changes

### config.json (replaces aliases.json)

```json
{
  "default_instance": "prod",
  "instances": {
    "prod": {
      "url": "https://myapp.datasette.cloud",
      "default_database": "main"
    },
    "local": {
      "url": "http://localhost:8001",
      "default_database": null
    }
  }
}
```

### auth.json (same file, new key structure)

Keys are now alias names instead of URLs:

```json
{
  "prod": "dstok_abc123",
  "local": "dstok_def456"
}
```

When no alias exists (using `-i` with a raw URL), tokens are looked up by URL with the existing prefix-matching logic as a fallback.

### Migration

On first run, if `config.json` doesn't exist but `aliases.json` does:

- Parse each v1 alias URL. If it has a single path segment (e.g., `https://example.com/mydb`), split into instance URL + default database. Otherwise store the URL as-is.
- Migrate auth.json keys from URLs to alias names where a match exists, keep URL-keyed entries as fallbacks.
- Write new files, rename originals to `.bak`.

### Environment variables

| Variable | Purpose | Precedence |
|----------|---------|------------|
| `DATASETTE_URL` | Default instance URL (existing) | Below config default, above nothing |
| `DATASETTE_DATABASE` | Default database name (new) | Below config default, above auto-detect |
| `DATASETTE_TOKEN` | Auth token (existing) | Below stored token, above nothing |

---

## Two ways to query: explicit and shortcut

The design provides two distinct interfaces for running queries, optimized for different workflows.

### Explicit: `dclient query <database> <sql>`

Database is a required positional argument. No defaults involved. This is unambiguous and works well for zero-config usage and when switching between databases frequently.

```bash
dclient query fixtures "select * from facetable limit 5"
dclient query analytics "select count(*) from events" -i staging
```

### Shortcut: `dclient <sql>`

When the first argument doesn't match any subcommand, `click-default-group` routes it to a default command that uses the configured default instance and default database. Override either with flags.

```bash
dclient "select count(*) from users"                # default instance + default db
dclient "select count(*) from users" -d analytics   # override database
dclient "select count(*) from users" -i staging     # override instance
```

This is the daily-driver mode for people with a configured default instance and database.

### Implementation

```python
from click_default_group import DefaultGroup

@click.group(cls=DefaultGroup, default="default_query", default_if_no_args=False)
@click.version_option()
def cli():
    "A client CLI utility for Datasette instances"

@cli.command()
@click.argument("database")
@click.argument("sql")
@click.option("-i", "--instance")
@click.option("--token")
@click.option("-v", "--verbose", is_flag=True)
# ... output format options ...
def query(database, sql, instance, token, verbose, **kwargs):
    """Run a SQL query against a Datasette database

    Requires both a database name and a SQL string.

    Example:

        dclient query fixtures "select * from facetable limit 5"
    """
    ...

@cli.command(name="default_query", hidden=True)
@click.argument("sql")
@click.option("-i", "--instance")
@click.option("-d", "--database")
@click.option("--token")
@click.option("-v", "--verbose", is_flag=True)
# ... output format options ...
def default_query(sql, instance, database, token, verbose, **kwargs):
    """Run a SQL query using default instance and database."""
    # Resolve instance and database from defaults/env vars
    # Error if no default database can be resolved
    ...
```

The `default_query` command is hidden from help output. Users see `query` in the help text; the bare-SQL shortcut just works without being documented as a separate command.

---

## Instance resolution

Every command that talks to a Datasette server accepts `-i, --instance TEXT`. Resolution order:

1. `-i` flag (alias name or URL)
2. `config.default_instance`
3. `DATASETTE_URL` environment variable
4. Error

If the value starts with `http://` or `https://`, use it as a URL directly. Otherwise look it up as an alias name in config.

---

## Database resolution

There are two modes of database resolution depending on the command.

### Commands with required positional database

`query`, `insert`, `upsert`: the database is always the first positional argument. No resolution logic, no defaults. You must name the database.

### Commands with optional `-d` flag

`tables`, `schema`, and the default query shortcut: resolve in order:

1. `-d` flag
2. Instance's `default_database` from config
3. `DATASETTE_DATABASE` environment variable
4. Auto-detect if instance has exactly one (non-internal) database
5. Error with a helpful message listing available databases

### Commands that don't need a database

`databases`, `plugins`, `actor`, `alias`, `auth`: no database argument or flag.

---

## New commands

### `dclient databases`

List databases on an instance.

```bash
$ dclient databases
main
extra

$ dclient databases --json
[{"name": "main", "tables_count": 12, ...}, ...]

$ dclient databases -i https://latest.datasette.io
fixtures
```

Options: `-i`, `--json`.

Implementation: `GET <instance>/.json` → `databases` key.

### `dclient tables`

List tables (and optionally views) in a database.

```bash
$ dclient tables
facetable          15 rows
facet_cities        4 rows

$ dclient tables -d analytics
events             1503 rows

$ dclient tables --views --json
[{"name": "facetable", "columns": [...], "count": 15, ...}, ...]
```

Options: `-i`, `-d`, `--views`, `--views-only`, `--hidden`, `--json`.

Implementation: `GET <instance>/<database>.json` → `tables` and `views` keys.

### `dclient schema`

Show SQL schema for a database or a specific table.

```bash
$ dclient schema
# all CREATE TABLE/VIEW statements for default database

$ dclient schema -d analytics
# all schemas for the analytics database

$ dclient schema facetable
# just that table's schema (in default database)

$ dclient schema facetable -d analytics
# that table in a specific database
```

The optional table name is a positional argument. Options: `-i`, `-d`, `--json`.

### `dclient plugins`

List installed plugins on an instance.

```bash
$ dclient plugins
datasette-files
datasette-auth-tokens

$ dclient plugins --json
[{"name": "datasette-files", "version": "0.3.1", ...}, ...]
```

Options: `-i`, `--json`.

Implementation: `GET <instance>/-/plugins.json`.

---

## Changed commands

### `dclient query`

```bash
# v1
dclient query https://datasette.io/content "select * from news"

# v2: database is required positional, instance is a flag
dclient query content "select * from news" -i https://datasette.io
dclient query fixtures "select * from facetable"    # uses default instance
```

Signature: `dclient query <database> <sql> [-i instance] [--csv|--tsv|--nl|--table] [-o file] [--token TOKEN] [-v]`

### `dclient insert`

```bash
# v1
dclient insert https://myapp.datasette.cloud/data mytable data.csv --csv

# v2: database and table are required positionals, instance is a flag
dclient insert main mytable data.csv --csv -i myapp
dclient insert main mytable data.csv --csv          # uses default instance
```

Signature: `dclient insert <database> <table> <file> [-i instance] [--csv|--tsv|--json|--nl] [--create] [--replace] [--ignore] [--alter] [--pk col] [--batch-size N] [--interval N] [--token TOKEN] [-v] [--silent]`

### `dclient upsert`

New command. Same shape as `insert` but hits `/-/upsert`.

Signature: `dclient upsert <database> <table> <file> [-i instance] [--csv|--tsv|--json|--nl] [--alter] [--pk col] [--batch-size N] [--interval N] [--token TOKEN] [-v] [--silent]`

### `dclient alias`

```bash
dclient alias add <name> <url>         # url is the instance root, stored as-is
dclient alias remove <name>
dclient alias list                     # shows * for default, (db: x) for default db
dclient alias default [name]           # set/show default instance
dclient alias default --clear
dclient alias default-db <alias> [db]  # set/show default database for an alias
dclient alias default-db <alias> --clear
```

**Tip: multiple aliases for the same instance.** You can create several aliases pointing at the same instance URL with different default databases. This gives you short names for databases you switch between frequently:

```bash
dclient alias add prod https://myapp.datasette.cloud
dclient alias add prod-analytics https://myapp.datasette.cloud
dclient alias default-db prod main
dclient alias default-db prod-analytics analytics

dclient tables -i prod              # → main
dclient tables -i prod-analytics    # → analytics
```

Auth tokens are resolved by alias name first, then by URL match as a fallback, so a token stored for either alias will work for both.

### `dclient auth`

```bash
dclient auth add <alias-or-url>           # prompt for token
dclient auth add <alias-or-url> --token TOKEN
dclient auth remove <alias-or-url>
dclient auth list                         # shows which aliases have tokens, never values
dclient auth status [-i instance]         # calls /-/actor.json to verify
```

### `dclient actor`

Uses `-i` flag instead of positional URL:

```bash
dclient actor                  # default instance
dclient actor -i prod
```

---

## Worked examples for the three usage modes

### Mode 1: Zero config, public instance

```bash
# Explicit database, instance as flag
dclient databases -i https://latest.datasette.io
dclient tables -i https://latest.datasette.io -d fixtures
dclient query fixtures "select * from facetable limit 3" -i https://latest.datasette.io

# Or set env vars for a session
export DATASETTE_URL=https://latest.datasette.io
export DATASETTE_DATABASE=fixtures
dclient tables
dclient "select * from facetable limit 3"
```

### Mode 2: Single default instance

```bash
# One-time setup
dclient alias add work https://myapp.datasette.cloud
dclient alias default work
dclient alias default-db work main
dclient auth add work

# Daily use — bare SQL shortcut uses defaults
dclient tables
dclient "select count(*) from users"
dclient "select * from events" -d analytics

# Explicit query when switching databases frequently
dclient query main "select count(*) from users"
dclient query analytics "select count(*) from events"

# Insert always names the database
dclient insert main events data.csv --csv --create --pk id
dclient plugins
```

### Mode 3: Multiple aliases

```bash
dclient alias add prod https://prod.datasette.cloud
dclient alias add staging https://staging.datasette.cloud
dclient alias default prod
dclient alias default-db prod main
dclient alias default-db staging main

# Bare shortcut hits prod/main
dclient "select count(*) from users"

# Explicit query — name the database, override instance with -i
dclient query main "select count(*) from users" -i staging
dclient query analytics "select * from events" -i staging

# Insert always explicit
dclient insert main events data.csv --csv -i staging
```

---

## Not in this version (reserved)

These command names are reserved for future work:

- `dclient cloud` — Datasette Cloud integration
- `dclient files` — datasette-files management
- `dclient get`, `dclient rows`, `dclient update`, `dclient delete` — row-level CRUD
- `dclient create-table`, `dclient drop-table` — DDL
- `dclient queries` — canned queries