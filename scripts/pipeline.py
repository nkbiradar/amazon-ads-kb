#!/usr/bin/env python3
"""
Amazon Ads Knowledge Base Pipeline - Master Orchestration Script

This script orchestrates the full knowledge acquisition pipeline:
Discover → Extract → Validate → Merge → Publish

DESIGN NOTE - Code vs Claude Split:

This pipeline uses a hybrid approach where deterministic operations are handled
by Python code, while knowledge extraction and validation are handled by Claude
AI subagents.

PURE PYTHON (Deterministic Operations):
- Configuration loading and parsing
- Content hash checking and source tracking
- Looping and orchestration logic
- Progress logging and summary generation
- File I/O for databases and logs

CLAUDE SUBAGENTS (AI-Powered Operations):
- Scout: Discovering related sources from seed URLs
- Extractor: Extracting factual claims from content
- Validator: Checking facts against existing knowledge
- Merger: Writing OKF documents with proper formatting

SUBAGENT INVOCATION:
In production, subagents are invoked using Claude Code's Agent tool or through
the Claude Code agent system. For this orchestration script, we use placeholder
functions that would be replaced with actual Claude Code agent invocations.

The subagent calls are marked clearly below with comments explaining how they
would be invoked in the actual Claude Code environment.

Usage:
    python scripts/pipeline.py --config sources/seed-urls.json
    python scripts/pipeline.py --url "https://advertising.amazon.com/docs" --type official
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Configuration
SOURCES_FILE = Path("sources/sources.json")
SEED_CONFIG_FILE = Path("sources/seed-urls.json")
HASH_CHECK_SCRIPT = Path("scripts/hash_check.py")
LOG_FILE = Path("knowledge/log.md")


class PipelineOrchestrator:
    """Main pipeline orchestration class."""

    def __init__(self, config_path: Path = None):
        """Initialize pipeline orchestrator."""
        self.config_path = config_path or SEED_CONFIG_FILE
        self.sources_db = self._load_sources_db()
        self.stats = {
            "sources_processed": 0,
            "sources_skipped": 0,
            "sources_failed": 0,
            "facts_extracted": 0,
            "facts_new": 0,
            "facts_duplicate": 0,
            "facts_conflict_resolved": 0,
            "documents_created": 0,
            "documents_updated": 0
        }
        self.start_time = datetime.utcnow()

    def _load_sources_db(self) -> Dict:
        """Load the sources tracking database."""
        if not SOURCES_FILE.exists():
            return {"sources": {}}

        try:
            with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self._log(f"Error loading sources database: {e}")
            return {"sources": {}}

    def _save_sources_db(self, db: Dict) -> None:
        """Save the sources tracking database."""
        try:
            db["metadata"] = db.get("metadata", {})
            db["metadata"]["last_updated"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            db["metadata"]["total_sources"] = len(db.get("sources", {}))

            SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SOURCES_FILE, 'w', encoding='utf-8') as f:
                json.dump(db, f, indent=2, ensure_ascii=False)
        except IOError as e:
            self._log(f"Error saving sources database: {e}")

    def _log(self, message: str) -> None:
        """Log progress message."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"[{timestamp}] {message}")

    def _run_hash_check(self, url: str, content: str) -> str:
        """
        Run hash check script to detect content changes.

        Args:
            url: Source URL to check
            content: Current content from the URL

        Returns:
            One of: "new", "unchanged", or "changed"
        """
        try:
            result = subprocess.run(
                [sys.executable, str(HASH_CHECK_SCRIPT), url, content],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self._log(f"Hash check failed: {e.stderr}")
            return "error"

    def fetch_content(self, url: str) -> str:
        """
        Fetch content from URL (placeholder).

        In production, this would use playwright MCP or web reader.
        For now, returns empty string as placeholder.
        """
        # Placeholder: In production, use playwright MCP
        # return fetch_page_content_playwright(url)
        self._log(f"Fetching content from {url}... (placeholder)")
        return ""

    # ========================================================================
    # SUBAGENT INVOCATION METHODS
    # ========================================================================
    # These methods show where Claude AI subagents would be invoked.
    # In actual Claude Code environment, these would use the Agent tool
    # or the Claude Code agent invocation system.
    # ========================================================================

    def invoke_scout_agent(self, url: str, source_type: str) -> List[Dict]:
        """
        Invoke Scout subagent to discover related sources.

        CLAUDE SUBAGENT INVOCATION:
        In production, this would be invoked as:
        result = await Agent(
            name="scout",
            prompt=f"Discover Amazon Ads sources related to: {url}",
            agentType="scout"
        )

        The scout agent would return:
        [
          {"url": "https://...", "source_type": "official"},
          {"url": "https://...", "source_type": "community"}
        ]

        For this orchestration script, returns placeholder data.
        """
        self._log(f"Scout: Discovering sources for {url}...")
        # Placeholder: Would invoke Claude Scout agent
        return [{"url": url, "source_type": source_type}]

    def invoke_extractor_agent(self, url: str, source_type: str, content: str) -> List[Dict]:
        """
        Invoke Extractor subagent to extract facts from content.

        CLAUDE SUBAGENT INVOCATION:
        In production, this would be invoked as:
        result = await Agent(
            name="extractor",
            prompt=f"Extract facts from {url}",
            input_data={"url": url, "source_type": source_type, "content": content},
            agentType="general-purpose"  # or use extractor agent definition
        )

        The extractor agent would return:
        [
          {
            "fact": "Amazon Ads supports sponsored products...",
            "source_url": url,
            "source_type": source_type,
            "confidence": "high"
          }
        ]

        For this orchestration script, returns placeholder data.
        """
        self._log(f"Extractor: Processing {url}...")
        # Placeholder: Would invoke Claude Extractor agent
        return []

    def invoke_validator_agent(self, facts: List[Dict]) -> Dict:
        """
        Invoke Validator subagent to check facts against existing knowledge.

        CLAUDE SUBAGENT INVOCATION:
        In production, this would be invoked as:
        result = await Agent(
            name="validator",
            prompt=f"Validate {len(facts)} facts against existing knowledge",
            input_data={"facts": facts},
            agentType="general-purpose"  # or use validator agent definition
        )

        The validator agent would return:
        {
          "validation_timestamp": "...",
          "facts_validated": [
            {
              "fact": "...",
              "status": "new",  # or "duplicate", "conflict-resolved"
              "reasoning": "...",
              "related_document": "...",
              "existing_fact": {...}
            }
          ]
        }

        For this orchestration script, returns placeholder data.
        """
        self._log(f"Validator: Checking {len(facts)} facts...")
        # Placeholder: Would invoke Claude Validator agent
        return {"validation_timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "facts_validated": []}

    def invoke_merger_agent(self, validation_report: Dict) -> Dict:
        """
        Invoke Merger subagent to merge validated facts into OKF documents.

        CLAUDE SUBAGENT INVOCATION:
        In production, this would be invoked as:
        result = await Agent(
            name="merger",
            prompt="Merge validated facts into knowledge base",
            input_data={"validation_report": validation_report},
            agentType="general-purpose"  # or use merger agent definition
        )

        The merger agent would return:
        {
          "merge_timestamp": "...",
          "documents_created": [...],
          "documents_updated": [...],
          "index_updated": true,
          "log_entry_added": true
        }

        For this orchestration script, returns placeholder data.
        """
        self._log(f"Merger: Creating/updating documents...")
        # Placeholder: Would invoke Claude Merger agent
        return {
            "merge_timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "documents_created": [],
            "documents_updated": [],
            "index_updated": False,
            "log_entry_added": False
        }

    # ========================================================================
    # PIPELINE STAGES
    # ========================================================================

    def process_source(self, url: str, source_type: str) -> bool:
        """
        Process a single source through the full pipeline.

        Stages:
        1. Hash check (skip if unchanged)
        2. Content fetch
        3. Extract facts
        4. Validate facts
        5. Merge into knowledge base

        Args:
            url: Source URL to process
            source_type: One of "official", "community", "blog"

        Returns:
            True if successful, False if failed
        """
        try:
            # Stage 1: Hash Check
            self._log(f"Processing: {url} ({source_type})")

            # Fetch content (placeholder)
            content = self.fetch_content(url)
            if not content:
                self._log(f"Failed to fetch content from {url}")
                self.stats["sources_failed"] += 1
                return False

            # Check if content has changed
            hash_status = self._run_hash_check(url, content)

            if hash_status == "unchanged":
                self._log(f"Skipping {url} - content unchanged")
                self.stats["sources_skipped"] += 1
                return True

            # Stage 2: Extract Facts
            facts = self.invoke_extractor_agent(url, source_type, content)
            if not facts:
                self._log(f"No facts extracted from {url}")
                self.stats["sources_failed"] += 1
                return False

            self.stats["facts_extracted"] += len(facts)

            # Stage 3: Validate Facts
            validation_report = self.invoke_validator_agent(facts)

            # Update statistics
            for fact_result in validation_report.get("facts_validated", []):
                status = fact_result.get("status", "unknown")
                if status == "new":
                    self.stats["facts_new"] += 1
                elif status == "duplicate":
                    self.stats["facts_duplicate"] += 1
                elif status == "conflict-resolved":
                    self.stats["facts_conflict_resolved"] += 1

            # Stage 4: Merge into Knowledge Base
            merge_report = self.invoke_merger_agent(validation_report)

            self.stats["documents_created"] += len(merge_report.get("documents_created", []))
            self.stats["documents_updated"] += len(merge_report.get("documents_updated", []))

            self.stats["sources_processed"] += 1
            self._log(f"Completed: {url}")
            return True

        except Exception as e:
            self._log(f"Error processing {url}: {e}")
            self.stats["sources_failed"] += 1
            return False

    def run_pipeline(self, sources: List[Dict]) -> None:
        """
        Run the full pipeline for all sources.

        Args:
            sources: List of source dictionaries with url, source_type, etc.
        """
        self._log("=" * 60)
        self._log("Amazon Ads Knowledge Base Pipeline")
        self._log("=" * 60)

        enabled_sources = [s for s in sources if s.get("enabled", True)]
        self._log(f"Processing {len(enabled_sources)} sources")

        # Process each source
        for source in enabled_sources:
            url = source["url"]
            source_type = source["source_type"]
            self.process_source(url, source_type)

        # Write summary to log
        self._write_summary()

    def _write_summary(self) -> None:
        """Write pipeline summary to knowledge/log.md."""
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()

        # Create log entry
        log_entry = f"""
## Pipeline Run: {self.start_time.strftime('%Y-%m-%dT%H:%M:%SZ')}

**Duration**: {duration:.2f} seconds
**Sources Processed**: {self.stats['sources_processed']}
**Sources Skipped**: {self.stats['sources_skipped']}
**Sources Failed**: {self.stats['sources_failed']}

**Statistics**:
- Facts extracted: {self.stats['facts_extracted']}
- Facts new: {self.stats['facts_new']}
- Facts duplicate: {self.stats['facts_duplicate']}
- Facts conflict-resolved: {self.stats['facts_conflict_resolved']}
- Documents created: {self.stats['documents_created']}
- Documents updated: {self.stats['documents_updated']}

---

"""

        # Append to log file
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            self._log(f"Summary written to {LOG_FILE}")
        except IOError as e:
            self._log(f"Error writing log: {e}")

        # Print final summary
        self._log("=" * 60)
        self._log("Pipeline Summary")
        self._log("=" * 60)
        self._log(f"Sources processed: {self.stats['sources_processed']}")
        self._log(f"Sources skipped: {self.stats['sources_skipped']}")
        self._log(f"Sources failed: {self.stats['sources_failed']}")
        self._log(f"Facts extracted: {self.stats['facts_extracted']}")
        self._log(f"Documents created: {self.stats['documents_created']}")
        self._log(f"Documents updated: {self.stats['documents_updated']}")
        self._log("=" * 60)


def load_config(config_path: Path) -> Dict:
    """Load pipeline configuration from JSON file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Amazon Ads Knowledge Base Pipeline"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=SEED_CONFIG_FILE,
        help="Path to seed URLs configuration file"
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Single URL to process (overrides config)"
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["official", "community", "blog"],
        help="Source type for single URL"
    )

    args = parser.parse_args()

    # Initialize orchestrator
    orchestrator = PipelineOrchestrator(args.config)

    # Determine sources to process
    if args.url:
        # Single source mode
        if not args.type:
            print("Error: --type required when using --url", file=sys.stderr)
            sys.exit(1)

        sources = [{
            "url": args.url,
            "source_type": args.type,
            "enabled": True
        }]
    else:
        # Config file mode
        config = load_config(args.config)
        sources = config.get("seeds", [])

    # Run pipeline
    orchestrator.run_pipeline(sources)


if __name__ == "__main__":
    main()
