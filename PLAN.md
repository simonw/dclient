# dclient Improvement Plan

## Feature Gap Analysis: dclient vs Datasette

### What dclient currently supports

| Feature | Status |
|---------|--------|
| SQL query execution (`query`) | Supported |
| Bulk data insertion (`insert`) | Supported (CSV, TSV, JSON, JSONL) |
| Actor/token introspection (`actor`) | Supported |
| URL aliases (`alias add/list/remove`) | Supported |
| Token storage (`auth add/list/remove`) | Supported |
| Bearer token authentication | Supported |
| Progress bar for inserts | Supported |
| Verbose/debug mode | Supported |
| Datasette plugin (`datasette dc`) | Supported |

### What Datasette exposes that dclient does NOT cover

#### Read Operations (high value)

| Datasette Feature | API Endpoint | dclient Status |
|-------------------|-------------|----------------|
| List databases | `GET /-/databases.json` | **Missing** |
| List tables/views in a database | `GET /{db}.json` | **Missing** |
| Browse/filter table rows | `GET /{db}/{table}.json?filters...` | **Missing** |
| Get single row by PK | `GET /{db}/{table}/{pk}.json` | **Missing** |
| Table schema inspection | `GET /{db}/{table}/-/schema.json` | **Missing** |
| Database schema inspection | `GET /{db}/-/schema.json` | **Missing** |
| Full-text search | `?_search=term` | **Missing** |
| Column filtering (exact, gt, lt, contains, etc.) | `?col__op=val` | **Missing** |
| Faceted browsing | `?_facet=col` | **Missing** |
| Sorting | `?_sort=col` / `?_sort_desc=col` | **Missing** |
| Pagination | `?_next=cursor&_size=N` | **Missing** |
| Column selection | `?_col=a&_col=b` / `?_nocol=x` | **Missing** |
| CSV/TSV export of table data | `GET /{db}/{table}.csv` | **Missing** |
| Canned queries listing | metadata in `GET /{db}.json` | **Missing** |

#### Write Operations (high value)

| Datasette Feature | API Endpoint | dclient Status |
|-------------------|-------------|----------------|
| Row upsert (insert-or-update) | `POST /{db}/{table}/-/upsert` | **Missing** |
| Update a single row | `POST /{db}/{table}/{pk}/-/update` | **Missing** |
| Delete a single row | `POST /{db}/{table}/{pk}/-/delete` | **Missing** |
| Drop a table | `POST /{db}/{table}/-/drop` | **Missing** |
| Create empty table with schema | `POST /{db}/-/create` (columns only) | **Missing** |

#### Metadata/Admin (medium value)

| Datasette Feature | API Endpoint | dclient Status |
|-------------------|-------------|----------------|
| Instance version info | `GET /-/versions.json` | **Missing** |
| Installed plugins | `GET /-/plugins.json` | **Missing** |
| Instance settings | `GET /-/settings.json` | **Missing** |
| Token creation | `POST /-/create-token` | **Missing** |
| Permission checks | `GET /-/allowed.json` | **Missing** |

---

## Proposed Plan

The plan is organized into tiers by impact and complexity, with the most
valuable additions first.

---

### Tier 1 -- Core Table Browsing & Schema Exploration

These commands turn dclient from "a way to run raw SQL" into a genuine
database exploration tool. They make up the biggest gap today: a user who
wants to see what tables exist or browse rows must either open a browser
or hand-craft SQL.

#### 1.1 `dclient databases` -- List databases

```
dclient databases <instance_url_or_alias>
```

Hits `GET {url}/-/databases.json`. Prints a table of database names, sizes,
and whether they are mutable. Add `--json` for raw JSON output.

#### 1.2 `dclient tables` -- List tables and views

```
dclient tables <db_url_or_alias>          # e.g. https://latest.datasette.io/fixtures
dclient tables <db_url_or_alias> --views  # include views
dclient tables <db_url_or_alias> --counts # include row counts
dclient tables <db_url_or_alias> --schema # include CREATE TABLE SQL
```

Hits `GET {db}.json`. Prints table names, row counts, and column lists.
`--json` for raw JSON.

#### 1.3 `dclient schema` -- Show table/database schema

```
dclient schema <db_url_or_alias>                     # full database schema
dclient schema <db_url_or_alias>/<table>             # single table schema
```

Hits `GET {db}/-/schema.json` or `GET {db}/{table}/-/schema.json`.
Outputs the `CREATE TABLE` / `CREATE VIEW` SQL.

#### 1.4 `dclient rows` -- Browse table rows with filtering

This is the biggest single feature addition. It exposes Datasette's
powerful table filtering API without requiring the user to write SQL.

```
dclient rows <table_url_or_alias> [OPTIONS]
```

**Filter flags:**

```
--where 'column = value'        # maps to ?column__exact=value
--where 'column > 100'          # maps to ?column__gt=100
--where 'column contains foo'   # maps to ?column__contains=foo
--where 'column is null'        # maps to ?column__isnull
--where-sql 'age > 30'          # maps to ?_where=age > 30  (raw SQL)
```

Or a simpler column-value approach:

```
-w column=value                 # exact
-w column__gt=100               # pass Datasette filter operators directly
```

**Other flags:**

```
--sort column                   # ascending sort
--sort-desc column              # descending sort
--search 'full text query'      # FTS search (?_search=...)
--col name --col email          # select specific columns
--nocol description             # exclude columns
--facet column                  # facet counts
--size 50                       # page size (default 100)
--all                           # auto-paginate through all pages
--limit N                       # stop after N total rows
--csv                           # output as CSV
--tsv                           # output as TSV
--nl                            # output as newline-delimited JSON
--json                          # output as JSON (default)
--table                         # human-readable table format
```

**Pagination:**
By default, print one page of results. `--all` follows `next_url` to
fetch every page. `--limit N` caps total rows returned.

#### 1.5 `dclient get` -- Fetch a single row by primary key

```
dclient get <table_url_or_alias> <pk_value>
dclient get <table_url_or_alias> <pk1>,<pk2>   # compound key
```

Hits `GET {db}/{table}/{pk}.json`. Prints the row as JSON.

---

### Tier 2 -- Write Operations

dclient already supports `insert` and `create`. These additions round out
the full CRUD lifecycle.

#### 2.1 `dclient upsert` -- Insert or update rows

```
dclient upsert <db_url_or_alias> <table> <filepath> [OPTIONS]
```

Same interface as `insert` but hits the `/-/upsert` endpoint. Requires
rows to contain primary key columns.

Shares most code with `insert`; the main difference is the endpoint URL
and the absence of `--replace`/`--ignore` flags.

#### 2.2 `dclient update` -- Update a single row

```
dclient update <table_url_or_alias> <pk_value> <key=value> [<key=value> ...]
dclient update <table_url_or_alias> <pk_value> --input file.json
```

Hits `POST {db}/{table}/{pk}/-/update` with `{"update": {...}}`.

#### 2.3 `dclient delete` -- Delete rows

```
dclient delete <table_url_or_alias> <pk_value>
dclient delete <table_url_or_alias> <pk_value> --yes   # skip confirmation
```

Hits `POST {db}/{table}/{pk}/-/delete`. Prompts for confirmation unless
`--yes` is passed.

#### 2.4 `dclient drop` -- Drop a table

```
dclient drop <table_url_or_alias>
dclient drop <table_url_or_alias> --yes   # skip confirmation
```

Hits `POST {db}/{table}/-/drop` with `{"confirm": true}`. Shows row count
and asks for confirmation unless `--yes`.

#### 2.5 `dclient create-table` -- Create an empty table with explicit schema

```
dclient create-table <db_url_or_alias> <table_name> \
  --column id integer \
  --column name text \
  --column score float \
  --pk id
```

Hits `POST {db}/-/create` with a `columns` array instead of `rows`.
The existing `insert --create` handles creation-with-data; this handles
the schema-only case.

---

### Tier 3 -- Output & UX Improvements

#### 3.1 Multiple output formats for `query` and `rows`

Currently `query` only outputs JSON. Add:

```
--csv          # CSV output
--tsv          # TSV output
--nl           # newline-delimited JSON
--table        # human-readable ASCII table (like sqlite-utils)
--yaml         # YAML output (optional, low priority)
```

For `--table` output, use a simple column-aligned format or integrate
with `tabulate` / `rich` (consider keeping dependencies minimal).

A lightweight approach: `sqlite-utils` already has table-formatting
utilities that could be reused.

#### 3.2 Pipe-friendly defaults

Detect whether stdout is a TTY:
- **TTY**: default to `--table` (human-readable) output
- **Pipe**: default to JSON (machine-readable) output

This matches the UX convention of tools like `gh` and `jq`.

#### 3.3 `--output` / `-o` flag for writing to a file

```
dclient query ... -o results.csv --csv
dclient rows ... -o dump.json
```

#### 3.4 Streaming output for large result sets

For `--all` pagination mode and `--csv`/`--nl` formats, stream rows as
they arrive rather than buffering everything in memory. Write each page
to stdout immediately.

---

### Tier 4 -- Authentication Improvements

The current auth system works but has friction points. These changes
make it smoother.

#### 4.1 `dclient auth login` -- Browser-based authentication

```
dclient auth login <instance_url_or_alias>
```

Flow:
1. Open the user's browser to `{instance}/-/create-token`
2. Start a temporary local HTTP server to receive the token callback
3. User creates a token in the Datasette UI and pastes it, OR:
4. If the instance supports it, redirect back to the local server with the token
5. Store the token automatically via the existing auth system

For instances that don't support redirect, fall back to:
1. Open the browser to `/-/create-token`
2. Prompt the user to paste the token into the terminal

This is similar to how `gh auth login`, `gcloud auth login`, and
`heroku login` work.

#### 4.2 `dclient auth token` -- Create a token via the API

```
dclient auth token <instance_url_or_alias>
dclient auth token <instance_url_or_alias> --expires-after 3600
dclient auth token <instance_url_or_alias> --read-only
```

Hits `POST /-/create-token`. Requires an existing root token or session.
Prints the new token and optionally stores it.

#### 4.3 `dclient auth status` -- Validate stored credentials

```
dclient auth status <instance_url_or_alias>
```

Hits `/-/actor.json` with the stored token and prints:
- Whether the token is valid
- The actor identity (id, permissions)
- Token expiry if available

This is just a friendlier wrapper around the existing `actor` command,
integrated into the `auth` subgroup.

#### 4.4 Environment variable support

```
export DCLIENT_TOKEN=dstok_xxx
export DCLIENT_URL=https://my-datasette.example.com/mydb
```

Token resolution order (highest to lowest priority):
1. `--token` CLI flag
2. `DCLIENT_TOKEN` environment variable
3. Stored token in `auth.json` (existing behavior)

The `DCLIENT_URL` variable provides a default instance so users don't
have to type it every time:

```
export DCLIENT_URL=https://my-datasette.example.com/mydb
dclient tables                    # uses DCLIENT_URL
dclient query 'select 1'         # uses DCLIENT_URL
dclient rows mytable --limit 10  # uses DCLIENT_URL
```

#### 4.5 Keyring integration (optional, lower priority)

Instead of storing tokens in plaintext `auth.json`, optionally use the
system keyring via the `keyring` Python package. This keeps tokens
encrypted at rest on macOS (Keychain), Windows (Credential Vault), and
Linux (Secret Service / KWallet).

Make this opt-in: `dclient auth add --keyring <url>`. Fall back to the
current file-based storage if `keyring` is not installed.

---

### Tier 5 -- Discoverability & Convenience

#### 5.1 `dclient info` -- Instance overview

```
dclient info <instance_url_or_alias>
```

Hits `/-/versions.json`, `/-/plugins.json`, `/-/databases.json` in
parallel. Prints a summary:

```
Datasette 1.0.1
Python 3.12.1
SQLite 3.45.0
Databases: 3 (fixtures, content, ephemeral)
Plugins: 12 installed
```

#### 5.2 URL inference and shortcuts

Allow shorthand for common patterns:

```
# These should all work equivalently:
dclient rows https://latest.datasette.io/fixtures/facetable
dclient rows latest fixtures/facetable    # if 'latest' is an alias
dclient rows latest facetable             # if alias points to a database URL
```

The key insight: if an alias points to `https://x.com/dbname`, then
`dclient rows <alias> <table>` should construct
`https://x.com/dbname/table.json`.

Currently the alias is just a URL prefix that gets used verbatim. Making
the alias system slightly smarter about joining paths would reduce typing
significantly.

#### 5.3 `dclient config` -- Manage configuration

```
dclient config show              # print config directory and contents
dclient config path              # print config directory path
dclient config edit              # open config in $EDITOR
```

Useful for debugging when tokens or aliases aren't working as expected.

#### 5.4 Shell completions

Use Click's built-in shell completion support to generate completions
for bash, zsh, and fish:

```
dclient --install-completion bash
dclient --install-completion zsh
dclient --install-completion fish
```

Click 8.x supports this natively via `shell_complete`. This could also
dynamically complete alias names, database names, and table names by
querying the stored aliases.

---

### Tier 6 -- Advanced Features (lower priority)

#### 6.1 `dclient export` -- Bulk export table data

```
dclient export <table_url> -o data.csv --csv
dclient export <table_url> -o data.json --json
dclient export <table_url> -o data.db   # export to local SQLite
```

This is essentially `dclient rows --all` but optimized for bulk export:
- Streams using `?_stream=1` (CSV format) when available
- For JSON, auto-paginates using `_next` cursor
- For SQLite output, pipes into `sqlite-utils insert`

#### 6.2 Parallel insert for large files

When inserting very large files, optionally send batches in parallel:

```
dclient insert <url> <table> huge.csv --parallel 4
```

Uses a thread pool to send N batches concurrently. Would require
switching from synchronous `httpx` to `httpx.AsyncClient` or using
`concurrent.futures.ThreadPoolExecutor`.

#### 6.3 `dclient diff` -- Compare local and remote data

```
dclient diff local.db remote_alias/tablename
```

Compare a local SQLite table with a remote Datasette table. Show added,
removed, and modified rows. Useful for sync workflows.

---

## Implementation Notes

### Shared infrastructure to build first

Several of the proposed commands share common patterns. Before
implementing individual commands, refactor these into shared utilities:

1. **URL resolution helper**: Centralize the alias-lookup + URL-construction
   logic that is currently duplicated in every command. A single function
   like `resolve_url(url_or_alias, suffix=None)` that handles aliases,
   adds `.json` where appropriate, and joins path segments.

2. **Authenticated HTTP client helper**: A function or context manager
   that creates an `httpx.Client` with the right `Authorization` header
   and timeout, resolved from `--token` / env var / auth.json. This
   eliminates the repeated token-resolution boilerplate in every command.

3. **Output formatter**: A shared output module that handles `--json`,
   `--csv`, `--tsv`, `--nl`, `--table` flags consistently across all
   commands that return data.

4. **Pagination helper**: A generator that follows `next_url` links to
   yield all pages of results, used by `rows --all` and `export`.

### Dependency considerations

The current dependencies are minimal: `click`, `httpx`, `sqlite-utils`.
The proposed changes mostly stay within these. Potential additions:

- `tabulate` or `rich` for `--table` output (or implement a minimal
  version to avoid new deps)
- `keyring` for optional encrypted token storage (optional dependency)

### Backward compatibility

All proposed changes are additive (new commands and new flags). No
existing command signatures or behaviors change. The only subtle change
would be if TTY-detection changes the default output format of `query`,
which should be gated behind a major version bump or opt-in flag.

### Testing strategy

Each new command should follow the existing test patterns:
- Unit tests with `pytest-httpx` for HTTP mocking
- Integration tests against a real in-memory Datasette instance
  (as done in `test_insert.py`)
- `cogapp` for keeping `--help` output in docs in sync

---

## Priority Summary

| Priority | Feature | Rationale |
|----------|---------|-----------|
| **P0** | `databases`, `tables`, `schema` | Basic exploration; most-requested gap |
| **P0** | `rows` with filtering/sorting/pagination | Replaces need for raw SQL for common tasks |
| **P0** | Environment variable support (`DCLIENT_TOKEN`, `DCLIENT_URL`) | Near-zero effort, big UX win |
| **P1** | `get`, `update`, `delete`, `drop` | Completes CRUD lifecycle |
| **P1** | `upsert` | Natural complement to existing `insert` |
| **P1** | Multiple output formats (CSV, table, NL) | Makes `query`/`rows` output usable in pipelines |
| **P1** | `auth login` (browser-based) | Biggest auth UX improvement |
| **P2** | `create-table` (schema only) | Useful but `insert --create` covers most cases |
| **P2** | TTY-aware default output | Polish |
| **P2** | `auth status`, `auth token` | Convenience wrappers |
| **P2** | `info` | Nice discoverability |
| **P2** | URL inference / smarter aliases | Reduces typing |
| **P3** | `export` (bulk) | Covered by `rows --all` for most cases |
| **P3** | Shell completions | Polish |
| **P3** | Keyring integration | Security hardening |
| **P3** | Parallel insert | Performance optimization |
| **P3** | `diff` | Advanced workflow |
