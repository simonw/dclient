from dclient.utils import token_for_url, url_matches_prefix
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


@pytest.mark.parametrize(
    "url,tokens,expected",
    (
        ("https://foo.com/bar", {"https://foo.com": "foo"}, "foo"),
        ("https://foo.com/bar", {"https://foo.com/baz": "baz"}, None),
        (
            "https://foo.com/bar",
            {"https://foo.com": "foo", "https://foo.com/bar": "bar"},
            "bar",
        ),
        (
            "https://foo.com/bar/baz",
            {
                "https://foo.com": "foo",
                "https://foo.com/bar/baz": "baz",
                "https://foo.com/bar": "bar",
            },
            "baz",
        ),
    ),
)
def test_token_for_url(url, tokens, expected):
    # Should always return longest matching of the available options
    assert token_for_url(url, tokens) == expected
