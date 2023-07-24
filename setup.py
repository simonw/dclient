from setuptools import setup
import os

VERSION = "0.2"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="dclient",
    description="A client CLI utility for Datasette instances",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Simon Willison",
    url="https://github.com/simonw/dclient",
    project_urls={
        "Issues": "https://github.com/simonw/dclient/issues",
        "CI": "https://github.com/simonw/dclient/actions",
        "Changelog": "https://github.com/simonw/dclient/releases",
    },
    license="Apache License, Version 2.0",
    version=VERSION,
    packages=["dclient"],
    entry_points={
        "datasette": ["client = dclient.plugin"],
        "console_scripts": ["dclient = dclient.cli:cli"],
    },
    install_requires=["click", "httpx", "sqlite-utils"],
    extras_require={
        "test": [
            "pytest",
            "pytest-asyncio",
            "pytest-httpx",
            "cogapp",
            "pytest-mock",
            "datasette>=1.0a2",
        ]
    },
    python_requires=">=3.7",
)
