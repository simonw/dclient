# dclient

[![PyPI](https://img.shields.io/pypi/v/dclient.svg)](https://pypi.org/project/dclient/)
[![Changelog](https://img.shields.io/github/v/release/simonw/dclient?include_prereleases&label=changelog)](https://github.com/simonw/dclient/releases)
[![Tests](https://github.com/simonw/dclient/workflows/Test/badge.svg)](https://github.com/simonw/dclient/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/dclient/blob/master/LICENSE)

A client CLI utility for [Datasette](https://datasette.io/) instances.

Much of the functionality requires Datasette 1.0a2 or higher.

## Things you can do with dclient

- **Explore** databases, tables, schemas, and rows without writing SQL
- **Query** with SQL and get results as JSON, CSV, TSV, or formatted tables
- **Insert** data from CSV, TSV, JSON, or newline-delimited JSON files
- **Upsert** data (insert or update based on primary key)
- **Update** individual rows by primary key
- **Delete** rows or **drop** entire tables
- **Create tables** with explicit schemas
- Run queries against authenticated Datasette instances
- Create aliases and store authentication tokens for convenient access

## Installation

Install this tool using `pip`:
```bash
pip install dclient
```
If you want to install it in the same virtual environment as Datasette (to use it as a plugin) you can instead run:
```bash
datasette install dclient
```

## Quick start

```bash
# Explore a Datasette instance
dclient databases https://latest.datasette.io
dclient tables https://latest.datasette.io/fixtures
dclient schema https://latest.datasette.io/fixtures

# Browse rows with filtering and sorting
dclient rows https://latest.datasette.io/fixtures/facetable --table
dclient rows https://latest.datasette.io/fixtures/facetable -w state=CA --sort city

# Fetch a single row by primary key
dclient get https://latest.datasette.io/fixtures/facetable 1

# Run a SQL query
dclient query https://latest.datasette.io/fixtures "select * from facetable limit 1"
```

For write operations (requires authentication):

```bash
# Create a table
dclient create-table https://example.com/db mytable \
  --column id integer --column name text --pk id

# Insert data from a CSV file
dclient insert https://example.com/db mytable data.csv --create

# Update a row
dclient update https://example.com/db/mytable 42 name=Alice age=30

# Upsert from a JSON file
dclient upsert https://example.com/db mytable data.json --json

# Delete a row
dclient delete https://example.com/db/mytable 42 --yes

# Drop a table
dclient drop https://example.com/db/mytable --yes
```

To shorten URLs, create an alias:
```bash
dclient alias add fixtures https://latest.datasette.io/fixtures
dclient query fixtures "select * from facetable limit 1"
```

## Documentation

Visit **[dclient.datasette.io](https://dclient.datasette.io)** for full documentation on using this tool.

## Development

To contribute to this tool, first checkout the code. Then install dependencies and run tests using [uv](https://docs.astral.sh/uv/):
```bash
cd dclient
uv run pytest
```
To build the package:
```bash
uv build
```
