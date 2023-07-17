from dclient.utils import url_matches_prefix
import pytest


@pytest.mark.parametrize(
    "url,prefix_url,expected",
    (
        ("https://example.com/foo/bar", "https://example.com/foo", True),
        ("https://example.com/foo/bar2", "https://example.com/foo/bar", False),
        ("https://example.com/foo/bar/baz", "https://example.com/foo/bar", True),
        ("https://example.com/foo/bar/baz", "https://example.com/foo", True),
        ("https://example.com/foo.json", "https://example.com/foo", True),
        # different scheme
        (
            "http://example.com/foo/bar",
            "https://example.com/foo",
            False,
        ),
        # different netloc
        (
            "https://example.org/foo/bar",
            "https://example.com/foo",
            False,
        ),
        # exactly the same
        ("https://example.com/foo", "https://example.com/foo", True),
        # trailing '/'
        (
            "https://example.com/foo/bar",
            "https://example.com/foo/bar/",
            False,
        ),
        (
            "https://example.com/foo/bar/baz",
            "https://example.com/foo/bar/",
            True,
        ),
    ),
)
def test_url_matches_prefix(url, prefix_url, expected):
    assert url_matches_prefix(url, prefix_url) == expected
