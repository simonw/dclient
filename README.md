# dclient

[![PyPI](https://img.shields.io/pypi/v/dclient.svg)](https://pypi.org/project/dclient/)
[![Changelog](https://img.shields.io/github/v/release/simonw/dclient?include_prereleases&label=changelog)](https://github.com/simonw/dclient/releases)
[![Tests](https://github.com/simonw/dclient/workflows/Test/badge.svg)](https://github.com/simonw/dclient/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/dclient/blob/master/LICENSE)

A client CLI utility for [Datasette](https://datasette.io/) instances.

Much of the functionality requires Datasette 1.0a2 or higher.

## Things you can do with dclient

- Run SQL queries against Datasette and returning the results as JSON
- Run queries against authenticated Datasette instances
- Create aliases and store authentication tokens for convenient access to Datasette
- Insert data into Datasette using the [insert API](https://docs.datasette.io/en/latest/json_api.html#the-json-write-api) (Datasette 1.0 alpha or higher)

## Installation

Install this tool using `pip`:
```bash
pip install dclient
```
If you want to install it in the same virtual environment as Datasette (to use it as a plugin) you can instead run:
```bash
datasette install dclient
```
## Running a query

```bash
dclient query https://latest.datasette.io/fixtures "select * from facetable limit 1"
```
To shorten that, create an alias:
```bash
dclient alias add fixtures https://latest.datasette.io/fixtures
```
Then run it like this instead:
```bash
dclient query fixtures "select * from facetable limit 1"
```
## Documentation

Visit **[dclient.datasette.io](https://dclient.datasette.io)** for full documentation on using this tool.

## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment:
```bash
cd dclient
python -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
pip install -e '.[test]'
```
To run the tests:
```bash
pytest
```
