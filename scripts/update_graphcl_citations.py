#!/usr/bin/env python3

import os
import re
import sys
from pathlib import Path

import requests


SCHOLAR_ID = "Pv-V2igAAAAJ"
ABOUT_FILE = Path("_pages/about.md")

TARGET_TITLES = {
    "Graph Contrastive Learning with Augmentations",
    "Graph Contrastive Learning Automated",
    "Bringing Your Own View: Graph Contrastive Learning without Prefabricated Data Augmentations",
}

START_MARKER = "<!-- graphcl-citations-start -->"
END_MARKER = "<!-- graphcl-citations-end -->"


def normalize_title(title):
    return " ".join(title.casefold().split())


def fetch_publications():
    api_key = os.environ.get("SERPAPI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "SERPAPI_API_KEY is not available. "
            "Check the GitHub Actions repository secret."
        )

    try:
        response = requests.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google_scholar_author",
                "author_id": SCHOLAR_ID,
                "hl": "en",
                "num": 100,
                "api_key": api_key,
            },
            timeout=60,
        )
    except requests.RequestException:
        raise RuntimeError("Unable to connect to SerpAPI.")

    if response.status_code != 200:
        raise RuntimeError(
            f"SerpAPI returned HTTP status {response.status_code}."
        )

    data = response.json()

    if "error" in data:
        raise RuntimeError(f"SerpAPI error: {data['error']}")

    articles = data.get("articles", [])

    if not articles:
        raise RuntimeError("SerpAPI returned no Google Scholar articles.")

    publications = {}

    for article in articles:
        title = article.get("title")

        if not title:
            continue

        citations = article.get("cited_by", {}).get("value", 0)
        print(article, title, citations)
        publications[normalize_title(title)] = int(citations)

    return publications


def update_about_page(total):
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
