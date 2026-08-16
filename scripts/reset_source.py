#!/usr/bin/env python3
"""
Clear a source's stored hash/last_checked entry in sources/sources.json so
the next pipeline run re-processes it instead of skipping it as unchanged.

Usage:
    python scripts/reset_source.py "https://advertising.amazon.com/library/guides/basics-of-amazon-attribution"

With no URL argument, lists the currently tracked source URLs instead of
changing anything.
"""

import json
import sys
from pathlib import Path

SOURCES_PATH = Path(__file__).resolve().parent.parent / "sources" / "sources.json"


def main():
    data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = data.get("sources", {})

    if len(sys.argv) < 2:
        print("Tracked source URLs:")
        for url in sources:
            print(f"  {url}")
        print("\nUsage: python scripts/reset_source.py \"<url>\"")
        return

    url = sys.argv[1]
    if url not in sources:
        print(f"URL not found in sources.json: {url}")
        print("Tracked source URLs:")
        for tracked_url in sources:
            print(f"  {tracked_url}")
        sys.exit(1)

    del sources[url]
    SOURCES_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Cleared hash entry for: {url}")
    print("Next pipeline run against this URL will re-process it instead of skipping.")


if __name__ == "__main__":
    main()
