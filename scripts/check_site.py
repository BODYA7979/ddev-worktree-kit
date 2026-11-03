"""Check built HTML links/assets for root and project-subpath deployments."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag, urljoin, urlsplit


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.references = []
        self.ids = set()
        self.language = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "html":
            self.language = values.get("lang")
        key = (
            "href"
            if tag in ("a", "link")
            else "src"
            if tag in ("script", "img", "source")
            else None
        )
        if key and values.get(key):
            self.references.append((values[key], tag == "a"))


def check_site(directory, site_url):
    directory = directory.resolve()
    base = urlsplit(site_url.rstrip("/") + "/")
    pages = {path: Page(path.read_text()) for path in directory.rglob("*.html")}
    for relative, language in (("index.html", "en"), ("uk/index.html", "uk")):
        if directory / relative not in pages or pages[directory / relative].language != language:
            raise ValueError(f"Missing {language} entry page/language")
    count = 0
    for path, page in pages.items():
        page_url = urljoin(site_url.rstrip("/") + "/", path.relative_to(directory).as_posix())
        for reference, check_anchor in page.references:
            target_url, fragment = urldefrag(urljoin(page_url, reference))
            target = urlsplit(target_url)
            if target.scheme not in ("http", "https") or target.netloc != base.netloc:
                continue
            if not target.path.startswith(base.path):
                raise ValueError(
                    f"Link escapes the Pages project subpath: {reference} in {path.name}"
                )
            relative = unquote(target.path[len(base.path) :])
            destination = (directory / relative).resolve()
            if not destination.is_relative_to(directory):
                raise ValueError("Generated link escapes the output directory")
            if destination.is_dir():
                destination /= "index.html"
            if not destination.is_file():
                raise ValueError(
                    f"Missing generated target: {reference} from {path.relative_to(directory)}"
                )
            if (
                check_anchor
                and fragment
                and destination in pages
                and unquote(fragment) not in pages[destination].ids
            ):
                raise ValueError(f"Missing anchor: {reference} from {path.relative_to(directory)}")
            count += 1
    return len(pages), count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--site-url", required=True)
    args = parser.parse_args()
    try:
        pages, links = check_site(args.directory, args.site_url)
    except ValueError as error:
        parser.exit(1, f"site: {error}\n")
    print(f"Site links/assets: PASS ({pages} HTML pages, {links} references)")
