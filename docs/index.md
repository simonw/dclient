# dclient

[![PyPI](https://img.shields.io/pypi/v/dclient.svg)](https://pypi.org/project/dclient/)
[![Changelog](https://img.shields.io/github/v/release/simonw/dclient?include_prereleases&label=changelog)](https://github.com/simonw/dclient/releases)
[![Tests](https://github.com/simonw/dclient/workflows/Test/badge.svg)](https://github.com/simonw/dclient/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/dclient/blob/master/LICENSE)

A client CLI utility for [Datasette](https://datasette.io/) instances

## Installation

Install `dclient` using `pip` (or [pipx](https://pipxproject.github.io/pipx/):

```bash
pip install dclient
```

### As a Datasette plugin

If you also have Datasette installed in the same environment it will register itself as a command plugin:
```bash
datasette install dclient
```
This means you can run any of these commands using `datasette dc` instead, like this:
```bash
datasette dc --help
datasette dc query fixtures "select * from facetable limit 1" -i latest
```

## Contents

```{toctree}
---
maxdepth: 3
---
queries
aliases
defaults
authentication
inserting
environment
```
