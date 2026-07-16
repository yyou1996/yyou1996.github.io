#!/usr/bin/env python3

import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


SCHOLAR_ID = "Pv-V2igAAAAJ"
ABOUT_FILE = Path("_pages/about.md")

TARGET_TITLES = {
    "Graph Contrastive Learning with Augmentations",
    "Graph Contrastive Learning Automated",
    (
        "Bringing Your Own View: Graph Contrastive Learning "
        "without Prefabricated Data Augmentations"
    ),
}

START_MARKER = "<!-- graphcl-citations-start -->"
END_MARKER = "<!-- graphcl-citations-end -->"


def normalize_title(title):
    """Normalize titles before matching them."""
    return " ".join(title.casefold().split())


def fetch_publications():
    """Retrieve publications and citation counts from Google Scholar."""
    url = "https://scholar.google.com/citations"

    params = {
        "user": SCHOLAR_ID,
        "hl": "en",
        "pagesize": 100,
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
        )
    }

    last_error = None

    for attempt in range(3):
        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.select(".gsc_a_tr")

            if not rows:
                raise RuntimeError(
                    "Google Scholar returned no publication rows. "
                    "The request may have been rate-limited."
                )

            publications = {}

            for row in rows:
                title_element = row.select_one(".gsc_a_at")

                if title_element is None:
                    continue

                title = normalize_title(
                    title_element.get_text(" ", strip=True)
                )

                citation_element = row.select_one(".gsc_a_c a")

                if citation_element:
                    citation_text = citation_element.get_text(strip=True)
                    citations = (
                        int(citation_text)
                        if citation_text.isdigit()
                        else 0
                    )
                else:
                    citations = 0

                publications[title] = citations

            return publications

        except (requests.RequestException, RuntimeError) as error:
            last_error = error

            if attempt < 2:
                time.sleep(10 * (attempt + 1))

    raise RuntimeError(
        f"Unable to retrieve Google Scholar data: {last_error}"
    )


def update_about_page(total):
    """Replace the existing citation total in about.md."""
    content = ABOUT_FILE.read_text(encoding="utf-8")

    pattern = re.compile(
        rf"({re.escape(START_MARKER)})\s*\d+\s*"
        rf"({re.escape(END_MARKER)})"
    )

    replacement = rf"\g<1>{total}\g<2>"
    updated_content, replacements = pattern.subn(
        replacement,
        content,
    )

    if replacements != 1:
        raise RuntimeError(
            "Expected exactly one citation marker, "
            f"but found {replacements}."
        )

    ABOUT_FILE.write_text(updated_content, encoding="utf-8")


def main():
    publications = fetch_publications()

    counts = {}
    missing = []

    for title in TARGET_TITLES:
        normalized = normalize_title(title)

        if normalized not in publications:
            missing.append(title)
        else:
            counts[title] = publications[normalized]

    if missing:
        print("The following papers were not found:", file=sys.stderr)

        for title in missing:
            print(f"  - {title}", file=sys.stderr)

        sys.exit(1)

    total = sum(counts.values())

    for title in sorted(counts):
        print(f"{counts[title]:>5}  {title}")

    print(f"{total:>5}  Total")

    update_about_page(total)


if __name__ == "__main__":
    main()
