# dclient

[![PyPI](https://img.shields.io/pypi/v/dclient.svg)](https://pypi.org/project/dclient/)
[![Changelog](https://img.shields.io/github/v/release/simonw/dclient?include_prereleases&label=changelog)](https://github.com/simonw/dclient/releases)
[![Tests](https://github.com/simonw/dclient/workflows/Test/badge.svg)](https://github.com/simonw/dclient/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/dclient/blob/master/LICENSE)

A client CLI utility for Datasette instances

## Installation

Install this tool using `pip`:

    pip install dclient

## Usage

For help, run:

    dclient --help

You can also use:

    python -m dclient --help

## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment:

    cd dclient
    python -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
