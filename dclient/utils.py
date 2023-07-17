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
