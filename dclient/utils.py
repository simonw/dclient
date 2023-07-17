from urllib.parse import urlparse


def url_matches_prefix(url: str, prefix: str) -> bool:
    url_parsed = urlparse(url)
    prefix_parsed = urlparse(prefix)

    if (
        url_parsed.scheme != prefix_parsed.scheme
        or url_parsed.netloc != prefix_parsed.netloc
    ):
        return False

    if url_parsed.path == prefix_parsed.path:
        return True

    url_path = url_parsed.path

    # Add '/' to the end of the paths if they don't already end with '/'
    prefix_path = prefix_parsed.path

    # Special treatment for /foo.json
    if url_path.endswith(".json"):
        if prefix_path + ".json" == url_path:
            return True

    if not prefix_path.endswith("/"):
        prefix_path += "/"

    return url_path.startswith(prefix_path)


def token_for_url(url: str, tokens: dict) -> str:
    matches = []
    for prefix_url, token in tokens.items():
        if url_matches_prefix(url, prefix_url):
            matches.append((prefix_url, token))
    # Sort by length of prefix_url, so that the longest match is first
    matches.sort(key=lambda x: len(x[0]), reverse=True)
    if matches:
        return matches[0][1]
    return None
