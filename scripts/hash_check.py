#!/usr/bin/env python3
"""
Content Hash Checking Script for Amazon Ads Knowledge Base

This script enables safe re-run capability for the knowledge acquisition pipeline.
By tracking content hashes per source URL, we can detect whether content has changed
since the last fetch and skip unchanged sources.

Pipeline Safety Logic:
1. Before fetching a source, check if URL exists in sources.json
2. If exists: compare current content hash against stored hash
   - Unchanged: Skip extraction (use cached data)
   - Changed: Re-extract and update knowledge base
3. If new: Extract and add to sources.json

Usage:
    python scripts/hash_check.py <url> <content>

Returns:
    Prints one of: "new", "unchanged", or "changed"
    Exit code: 0 (success), 1 (error)
"""

import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime

# Configuration
SOURCES_FILE = Path("sources/sources.json")


def compute_content_hash(content: str) -> str:
    """
    Compute SHA-256 hash of normalized content.

    Normalization removes whitespace differences that don't affect content meaning:
    - Strip leading/trailing whitespace
    - Normalize internal whitespace to single spaces
    - This ensures "a  b" and "a b" hash the same

    Args:
        content: The content to hash (string)

    Returns:
        SHA-256 hash as hexadecimal string
    """
    if not content:
        return ""

    # Normalize content: remove extra whitespace
    normalized = " ".join(content.strip().split())

    # Compute SHA-256 hash
    return hashlib.sha256(normalized.encode()).hexdigest()


def load_sources_db() -> dict:
    """
    Load the sources tracking database from sources.json.

    Returns:
        Dictionary containing sources database structure
    """
    if not SOURCES_FILE.exists():
        return {"sources": {}}

    try:
        with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading sources database: {e}", file=sys.stderr)
        sys.exit(1)


def save_sources_db(db: dict) -> None:
    """
    Save the sources tracking database to sources.json.

    Args:
        db: Dictionary containing sources database structure
    """
    # Update metadata
    db["metadata"] = db.get("metadata", {})
    db["metadata"]["last_updated"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    db["metadata"]["total_sources"] = len(db.get("sources", {}))

    try:
        SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SOURCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving sources database: {e}", file=sys.stderr)
        sys.exit(1)


def check_source_hash(url: str, content: str) -> str:
    """
    Check if source content has changed since last fetch.

    This is the core logic for pipeline re-run safety:

    - If URL is new to the database: return "new"
    - If content hash matches stored hash: return "unchanged"
    - If content hash differs from stored hash: return "changed"

    Args:
        url: The source URL to check
        content: The current content from the URL

    Returns:
        One of: "new", "unchanged", or "changed"
    """
    # Compute hash of current content
    current_hash = compute_content_hash(content)

    # Load existing sources database
    db = load_sources_db()
    sources = db.get("sources", {})

    # Check if URL exists in database
    if url not in sources:
        return "new"

    # Get stored hash from last fetch
    stored_entry = sources[url]
    stored_hash = stored_entry.get("content_hash", "")

    # Compare hashes
    if current_hash == stored_hash:
        return "unchanged"
    else:
        return "changed"


def update_source_entry(url: str, content: str, status: str, source_type: str = "official") -> None:
    """
    Update or add a source entry in the sources database.

    Updates metadata including:
    - content_hash: Hash of the content
    - last_checked: Current timestamp (when we just checked)
    - last_changed: Timestamp when content last changed
    - fetch_count: Total number of times we've fetched this source
    - change_count: Total number of times content has changed

    Args:
        url: The source URL
        content: The current content from the URL
        status: One of "new", "unchanged", or "changed"
        source_type: One of "official", "community", "blog"
    """
    db = load_sources_db()
    sources = db.get("sources", {})

    # Compute hash of current content
    current_hash = compute_content_hash(content)

    # Get current timestamp
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    if url in sources:
        # Update existing entry
        entry = sources[url]
        entry["content_hash"] = current_hash
        entry["last_checked"] = now
        entry["fetch_count"] = entry.get("fetch_count", 0) + 1

        # Only update last_changed if content actually changed
        if status == "changed":
            entry["last_changed"] = now
            entry["change_count"] = entry.get("change_count", 0) + 1
    else:
        # Create new entry
        sources[url] = {
            "url": url,
            "content_hash": current_hash,
            "last_checked": now,
            "last_changed": now if status == "new" else now,
            "source_type": source_type,
            "fetch_count": 1,
            "change_count": 0
        }

    # Save updated database
    db["sources"] = sources
    save_sources_db(db)


def main():
    """
    Main entry point for hash checking.

    Expected command line arguments:
        arg1: URL to check
        arg2: Content from the URL

    Prints status and optionally updates database:
        "new" - URL not seen before
        "unchanged" - Content same as last fetch
        "changed" - Content different from last fetch
    """
    if len(sys.argv) != 3:
        print("Usage: python hash_check.py <url> <content>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    content = sys.argv[2]

    # Check if content has changed
    status = check_source_hash(url, content)

    # Print status for calling process
    print(status)

    # Update database with the new hash and metadata
    # Determine source_type - for new sources, default to "official" unless otherwise specified
    source_type = "official"
    db = load_sources_db()
    if url in db.get("sources", {}):
        source_type = db["sources"][url].get("source_type", "official")

    update_source_entry(url, content, status, source_type)


if __name__ == "__main__":
    main()
