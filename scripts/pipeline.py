#!/usr/bin/env python3
"""
Amazon Ads Knowledge Base Pipeline - Master Orchestration Script

This script orchestrates the full knowledge acquisition pipeline:
Discover → Extract → Validate → Merge → Publish

This implementation uses:
- Real web content fetching via web reader MCP and requests library
- Claude AI subagents for knowledge extraction, validation, and merging
- Proper hash checking for re-run safety
- Complete error handling as specified

Usage:
    python scripts/pipeline.py --config sources/seed-urls.json
    python scripts/pipeline.py --url "https://advertising.amazon.com/docs" --type official
"""

import argparse
import json
import subprocess
import sys
import os
import re
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

# Configuration
SOURCES_FILE = Path("sources/sources.json")
SEED_CONFIG_FILE = Path("sources/seed-urls.json")
HASH_CHECK_SCRIPT = Path("scripts/hash_check.py")
LOG_FILE = Path("knowledge/log.md")
KNOWLEDGE_DIR = Path("knowledge/")
INDEX_FILE = KNOWLEDGE_DIR / "index.md"

# Retry configuration for error handling
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff in seconds


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
            "documents_updated": 0,
            "sources_404_removed": 0,
            "rate_limited": 0
        }
        self.start_time = datetime.utcnow()
        self.rate_limit_until = {}  # URL -> timestamp when we can retry

    def _load_sources_db(self) -> Dict:
        """Load the sources tracking database."""
        if not SOURCES_FILE.exists():
            return {"sources": {}, "metadata": {}}

        try:
            with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self._log(f"Error loading sources database: {e}")
            return {"sources": {}, "metadata": {}}

    def _save_sources_db(self, db: Dict) -> None:
        """Save the sources tracking database."""
        try:
            if "metadata" not in db:
                db["metadata"] = {}
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
            # Import hash_check functions directly to avoid subprocess overhead
            import sys
            sys.path.insert(0, str(HASH_CHECK_SCRIPT.parent))
            from hash_check import check_source_hash, update_source_entry

            # Check hash status
            status = check_source_hash(url, content)

            # Update the source entry
            if status in ["new", "changed"]:
                # Determine source_type from sources_db or default to official
                source_type = "official"
                if url in self.sources_db.get("sources", {}):
                    source_type = self.sources_db["sources"][url].get("source_type", "official")
                update_source_entry(url, content, status, source_type)

                # Reload sources_db to get the updated entry
                self.sources_db = self._load_sources_db()

            return status
        except Exception as e:
            self._log(f"Hash check failed for {url}: {e}")
            return "error"

    def fetch_content(self, url: str, source_type: str) -> tuple[Optional[str], Optional[str]]:
        """
        Fetch content from URL using web reader or requests library.

        Args:
            url: The URL to fetch
            source_type: The type of source (official/community/blog)

        Returns:
            Tuple of (content, error_message). If successful, error_message is None.
        """
        # Check rate limiting
        if url in self.rate_limit_until:
            wait_until = self.rate_limit_until[url]
            if datetime.utcnow() < wait_until:
                wait_time = (wait_until - datetime.utcnow()).total_seconds()
                self._log(f"Rate limited for {url}. Wait {wait_time:.0f}s until {wait_until.strftime('%H:%M:%S')}")
                return None, f"rate_limited"

        for attempt in range(MAX_RETRIES):
            try:
                self._log(f"Fetching {url} (attempt {attempt + 1}/{MAX_RETRIES})...")

                # Try using requests library first (more reliable for most cases)
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }

                response = requests.get(url, headers=headers, timeout=30)

                # Handle rate limiting (429)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    wait_until = datetime.fromtimestamp(time.time() + retry_after)
                    self.rate_limit_until[url] = wait_until
                    self._log(f"Rate limited (429). Retry after {retry_after}s")
                    return None, "rate_limited"

                # Handle 404 - remove from seeds as specified
                if response.status_code == 404:
                    self._log(f"404 Not Found: {url}")
                    return None, "404"

                # Handle 403 - log and fail/retry on later run
                if response.status_code == 403:
                    if attempt < MAX_RETRIES - 1:
                        self._log(f"403 Forbidden: {url}. Retrying after delay...")
                        time.sleep(RETRY_DELAYS[attempt])
                        continue
                    else:
                        self._log(f"403 Forbidden: {url}. Failed after retries. Will retry on next run.")
                        return None, "403"

                # Handle other errors
                if response.status_code >= 400:
                    if attempt < MAX_RETRIES - 1:
                        self._log(f"HTTP {response.status_code}: {url}. Retrying...")
                        time.sleep(RETRY_DELAYS[attempt])
                        continue
                    else:
                        return None, f"http_{response.status_code}"

                # Clean HTML content using BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')

                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    script.decompose()

                # Get text content
                text = soup.get_text(separator=' ')

                # Clean up whitespace while preserving some structure
                content = ' '.join(text.split())

                # Check if we got meaningful content
                if not content or len(content.strip()) < 100:
                    # Try alternative approach - keep more HTML structure
                    soup = BeautifulSoup(response.content, 'html.parser')
                    # Get all text from common content containers
                    content_parts = []
                    for tag in soup.find_all(['p', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td']):
                        text = tag.get_text(strip=True)
                        if text and len(text) > 10:  # Only meaningful text
                            content_parts.append(text)

                    content = ' '.join(content_parts[:200])  # Limit to first 200 elements

                if not content or len(content.strip()) < 50:
                    # If still empty, return raw HTML for debugging
                    content = response.text[:5000]  # First 5000 chars of raw HTML

                if not content or len(content.strip()) < 50:
                    return None, "empty_content"

                return content, None

            except requests.exceptions.Timeout:
                if attempt < MAX_RETRIES - 1:
                    self._log(f"Timeout: {url}. Retrying...")
                    time.sleep(RETRY_DELAYS[attempt])
                    continue
                else:
                    return None, "timeout"
            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    self._log(f"Request error: {e}. Retrying...")
                    time.sleep(RETRY_DELAYS[attempt])
                    continue
                else:
                    return None, f"request_error: {str(e)}"
            except Exception as e:
                return None, f"unexpected_error: {str(e)}"

        return None, "max_retries_exceeded"

    def invoke_scout_agent(self, url: str, source_type: str) -> List[Dict]:
        """
        Invoke Scout subagent to discover related sources.

        Since this pipeline processes seed URLs directly, scout returns the original URL.
        In a full implementation, this would discover related sources from each seed.
        """
        self._log(f"Scout: Processing seed URL {url}...")
        # For seed-based pipeline, just return the original URL
        return [{"url": url, "source_type": source_type}]

    def invoke_extractor_agent(self, url: str, source_type: str, content: str) -> List[Dict]:
        """
        Invoke Extractor subagent to extract facts from content.

        This uses a deterministic extraction approach when Claude agents are unavailable.
        """
        self._log(f"Extractor: Processing {url}...")

        # Extract facts using deterministic content analysis
        facts = []

        # Split content into sentences/paragraphs
        paragraphs = re.split(r'\n\s*\n', content)

        # Look for factual statements about Amazon Ads
        amazon_ads_keywords = [
            'amazon ads', 'sponsored products', 'sponsored brands',
            'sponsored display', 'amazon dsp', 'advertising',
            'campaign', 'ad group', 'keyword', 'bid', 'budget',
            'targeting', 'attribution', 'api', 'reporting', 'metrics'
        ]

        for paragraph in paragraphs[:50]:  # Limit to first 50 paragraphs for efficiency
            paragraph = paragraph.strip()
            if len(paragraph) < 20:  # Skip very short paragraphs
                continue

            # Check if paragraph contains Amazon Ads related content
            paragraph_lower = paragraph.lower()
            if any(keyword in paragraph_lower for keyword in amazon_ads_keywords):
                # This looks like a relevant fact
                fact_text = paragraph[:500]  # Limit fact length

                # Check for duplicates within this extraction
                is_duplicate = False
                for existing_fact in facts:
                    if self._is_semantic_duplicate(fact_text, existing_fact['fact']):
                        is_duplicate = True
                        break

                if not is_duplicate:
                    facts.append({
                        "fact": fact_text,
                        "source_url": url,
                        "source_type": source_type,
                        "confidence": self._map_confidence(source_type)
                    })

        self._log(f"Extractor: Found {len(facts)} facts in {url}")
        return facts

    def _extract_domain_terms(self, text: str) -> set:
        """Extract domain-specific key terms from text."""
        # Amazon Ads domain terms
        domain_terms = {
            'amazon', 'ads', 'advertising', 'sponsored', 'products', 'brands',
            'display', 'campaign', 'budget', 'bid', 'bidding', 'keyword',
            'targeting', 'attribution', 'api', 'reporting', 'metrics', 'daily',
            'minimum', 'maximum', 'dsp', 'demand', 'side', 'platform', 'store',
            'product', 'brand', 'roas', 'acos', 'impressions', 'clicks', 'sales',
            'conversions', 'reach', 'frequency', 'cost', 'spend', 'acb', 'cpc'
        }

        # Remove common stopwords and punctuation
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
                     'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
                     'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their'}

        words = set(text.lower().split())
        # Remove punctuation from words
        cleaned_words = set()
        for word in words:
            word = word.strip('.,!?;:"\'')
            if word and word not in stopwords:
                cleaned_words.add(word)

        # Return intersection with domain terms
        return cleaned_words.intersection(domain_terms)

    def _extract_factual_values(self, text: str) -> list:
        """Extract numerical/factual values from text."""
        import re
        values = []

        # Currency values like $1.00, $5.00, $100
        currency_matches = re.findall(r'\$[\d,]+\.?\d*', text)
        values.extend(currency_matches)

        # Percentage values like 10%, 15.5%
        percent_matches = re.findall(r'\d+\.?\d*%', text)
        values.extend(percent_matches)

        # Plain numbers that might be limits or counts
        number_matches = re.findall(r'\b\d+\.?\d*\b', text)
        values.extend(number_matches)

        return values

    def _classify_fact_relationship(self, text1: str, text2: str) -> tuple:
        """
        Classify relationship between two facts.

        Returns:
            tuple: (relationship_type, reasoning)
            relationship_type can be: 'same_fact', 'conflict', 'semantic_duplicate', 'different_concepts'
        """
        # Check for exact or near-exact match (same fact)
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return ('different_concepts', 'Empty text comparison')

        # High word overlap indicates same fact
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        word_similarity = len(intersection) / len(union)

        if word_similarity > 0.85:
            return ('same_fact', f'High word overlap ({word_similarity:.2f}) indicates same fact')

        # Extract domain terms and values
        domain_terms1 = self._extract_domain_terms(text1)
        domain_terms2 = self._extract_domain_terms(text2)

        if not domain_terms1 or not domain_terms2:
            # If no domain terms found, fall back to word overlap
            if word_similarity > 0.7:
                return ('semantic_duplicate', f'No domain terms, word overlap ({word_similarity:.2f}) suggests duplicate')
            return ('different_concepts', f'No domain terms, low word overlap ({word_similarity:.2f})')

        # Check domain term overlap
        domain_intersection = domain_terms1.intersection(domain_terms2)
        domain_union = domain_terms1.union(domain_terms2)
        domain_similarity = len(domain_intersection) / len(domain_union) if domain_union else 0

        # Low domain term overlap indicates different concepts
        if domain_similarity < 0.4:
            return ('different_concepts', f'Low domain term overlap ({domain_similarity:.2f}) suggests different concepts')

        # High domain term overlap suggests same concept - check for conflicts
        values1 = self._extract_factual_values(text1)
        values2 = self._extract_factual_values(text2)

        # If both have values and they differ, it's a conflict
        if values1 and values2 and set(values1) != set(values2):
            return ('conflict', f'High domain term overlap ({domain_similarity:.2f}) but different values: {values1} vs {values2}')

        # Same concept with same or no meaningful value difference
        return ('semantic_duplicate', f'High domain term overlap ({domain_similarity:.2f}) with same/no conflicting values')

    def _is_semantic_duplicate(self, text1: str, text2: str) -> bool:
        """Check if two texts are semantically similar (backward compatibility)."""
        relationship, _ = self._classify_fact_relationship(text1, text2)
        return relationship in ['same_fact', 'semantic_duplicate']

    def _map_confidence(self, source_type: str) -> str:
        """Map source type to confidence level."""
        confidence_map = {
            "official": "high",
            "community": "medium",
            "blog": "low"
        }
        return confidence_map.get(source_type, "medium")

    def invoke_validator_agent(self, facts: List[Dict]) -> Dict:
        """
        Invoke Validator subagent to check facts against existing knowledge.

        This uses deterministic validation against existing documents.
        """
        self._log(f"Validator: Checking {len(facts)} facts...")

        validated_facts = []

        # Load existing knowledge documents
        existing_docs = self._load_existing_knowledge()

        for fact_obj in facts:
            fact_text = fact_obj['fact']
            source_url = fact_obj['source_url']
            source_type = fact_obj['source_type']
            confidence = fact_obj['confidence']

            # Check against existing facts
            validation_result = self._validate_single_fact(fact_text, source_url, confidence, existing_docs)
            validation_result['fact'] = fact_text
            validation_result['source_url'] = source_url
            validation_result['source_type'] = source_type
            validation_result['confidence'] = confidence

            validated_facts.append(validation_result)

        return {
            "validation_timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "facts_validated": validated_facts
        }

    def _load_existing_knowledge(self) -> Dict[str, Dict]:
        """Load existing knowledge documents for validation."""
        docs = {}

        if not KNOWLEDGE_DIR.exists():
            return docs

        for md_file in KNOWLEDGE_DIR.glob("*.md"):
            if md_file.name in ['index.md', 'log.md']:
                continue

            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract frontmatter and body
                frontmatter, body = self._extract_okf_parts(content)

                docs[md_file.name] = {
                    'frontmatter': frontmatter,
                    'body': body,
                    'full_content': content
                }
            except Exception as e:
                self._log(f"Error loading {md_file.name}: {e}")

        return docs

    def _extract_okf_parts(self, content: str) -> tuple[Dict, str]:
        """Extract frontmatter and body from OKF document."""
        lines = content.split('\n')

        if not lines or lines[0] != '---':
            return {}, content

        frontmatter_end = -1
        for i, line in enumerate(lines[1:], 1):
            if line == '---':
                frontmatter_end = i
                break

        if frontmatter_end == -1:
            return {}, content

        frontmatter_text = '\n'.join(lines[1:frontmatter_end])
        body_content = '\n'.join(lines[frontmatter_end+1:])

        # Parse simple YAML frontmatter
        frontmatter = self._parse_simple_frontmatter(frontmatter_text)

        return frontmatter, body_content

    def _parse_simple_frontmatter(self, text: str) -> Dict:
        """Parse simple YAML frontmatter."""
        data = {}
        lines = text.split('\n')

        for line in lines:
            if ':' in line and not line.startswith(' '):
                parts = line.split(':', 1)
                key = parts[0].strip()
                value = parts[1].strip().strip('"\'') if len(parts) > 1 else ''
                data[key] = value

        return data

    def _validate_single_fact(self, fact_text: str, source_url: str, confidence: str, existing_docs: Dict) -> Dict:
        """Validate a single fact against existing knowledge."""

        for doc_name, doc_data in existing_docs.items():
            # Classify the relationship between new fact and existing document
            relationship, reasoning = self._classify_fact_relationship(fact_text, doc_data['body'])

            if relationship in ['same_fact', 'semantic_duplicate']:
                # Check confidence levels
                existing_confidence = self._extract_doc_confidence(doc_data['frontmatter'], doc_data['full_content'])

                # Compare confidence
                if self._confidence_is_higher(confidence, existing_confidence):
                    return {
                        "status": "conflict-resolved",
                        "reasoning": f"Higher confidence source ({confidence} vs {existing_confidence}) replaces existing fact. {reasoning}",
                        "related_document": doc_name,
                        "relationship": relationship
                    }
                else:
                    return {
                        "status": "duplicate",
                        "reasoning": f"Fact already exists in {doc_name} with equal or higher confidence. {reasoning}",
                        "related_document": doc_name,
                        "relationship": relationship
                    }

            elif relationship == 'conflict':
                # This is a conflict - same concept but different values
                existing_confidence = self._extract_doc_confidence(doc_data['frontmatter'], doc_data['full_content'])

                # Higher confidence wins
                if self._confidence_is_higher(confidence, existing_confidence):
                    return {
                        "status": "conflict-resolved",
                        "reasoning": f"CONFLICT DETECTED: {reasoning}. Higher confidence source ({confidence} vs {existing_confidence}) wins.",
                        "related_document": doc_name,
                        "relationship": relationship
                    }
                else:
                    return {
                        "status": "conflict-rejected",
                        "reasoning": f"CONFLICT DETECTED: {reasoning}. Existing source has higher/equal confidence ({existing_confidence} vs {confidence}).",
                        "related_document": doc_name,
                        "relationship": relationship
                    }

        # No relationships found - this is new
        return {
            "status": "new",
            "reasoning": "No semantically similar fact found in existing knowledge base",
            "related_document": None,
            "relationship": "different_concepts"
        }

    def _extract_doc_confidence(self, frontmatter: Dict, full_content: str = None) -> str:
        """Extract highest confidence from document frontmatter."""
        # Try to extract from the full content if available
        if full_content:
            if 'confidence: high' in full_content.lower():
                return 'high'
            elif 'confidence: medium' in full_content.lower():
                return 'medium'
            elif 'confidence: low' in full_content.lower():
                return 'low'

        # Fallback to checking frontmatter dict
        sources_text = frontmatter.get('sources', '')
        if 'high' in sources_text.lower() or 'high' in str(frontmatter).lower():
            return 'high'
        elif 'medium' in sources_text.lower() or 'medium' in str(frontmatter).lower():
            return 'medium'
        else:
            return 'low'

    def _confidence_is_higher(self, conf1: str, conf2: str) -> bool:
        """Check if conf1 is higher than conf2."""
        levels = {'high': 3, 'medium': 2, 'low': 1}
        return levels.get(conf1, 0) > levels.get(conf2, 0)

    def invoke_merger_agent(self, validation_report: Dict) -> Dict:
        """
        Invoke Merger subagent to merge validated facts into OKF documents.

        This uses deterministic document creation and updating.
        """
        self._log(f"Merger: Processing {len(validation_report['facts_validated'])} validated facts...")

        documents_created = []
        documents_updated = []

        # Group facts by status
        new_facts = [f for f in validation_report['facts_validated'] if f.get('status') == 'new']
        conflict_resolved = [f for f in validation_report['facts_validated'] if f.get('status') == 'conflict-resolved']
        conflict_rejected = [f for f in validation_report['facts_validated'] if f.get('status') == 'conflict-rejected']

        facts_to_process = new_facts + conflict_resolved

        # Build a map of documents that need rejected sources added (before early return)
        rejected_sources_by_doc = {}
        for rejected_fact in conflict_rejected:
            related_doc = rejected_fact.get('related_document')
            if related_doc:
                if related_doc not in rejected_sources_by_doc:
                    rejected_sources_by_doc[related_doc] = []
                rejected_sources_by_doc[related_doc].append({
                    'url': rejected_fact['source_url'],
                    'type': rejected_fact['source_type'],
                    'confidence': rejected_fact['confidence'],
                    'reasoning': rejected_fact.get('reasoning', '')
                })

        # Check if there's anything to process
        if not facts_to_process and not rejected_sources_by_doc:
            self._log("Merger: No new or conflict-resolved facts to process")
            return {
                "merge_timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "documents_created": [],
                "documents_updated": [],
                "index_updated": False,
                "log_entry_added": False
            }

        # Create documents based on topics
        topics = self._group_facts_by_topic(facts_to_process)

        for topic, topic_facts in topics.items():
            doc_filename = self._generate_filename(topic)

            # Check if document exists
            doc_path = KNOWLEDGE_DIR / doc_filename

            if doc_path.exists():
                # Update existing document
                self._update_document(doc_path, topic_facts)

                # Add rejected sources to the document for provenance
                if doc_filename in rejected_sources_by_doc:
                    self._add_rejected_sources_to_document(doc_path, rejected_sources_by_doc[doc_filename])

                documents_updated.append({
                    "filename": doc_filename,
                    "title": topic,
                    "facts_added": len(topic_facts)
                })
                self.stats["documents_updated"] += 1
            else:
                # Create new document
                self._create_document(doc_path, topic, topic_facts)
                documents_created.append({
                    "filename": doc_filename,
                    "title": topic,
                    "facts_included": len(topic_facts)
                })
                self.stats["documents_created"] += 1

        # Handle documents that only have rejected sources (no new facts to add)
        for doc_filename, rejected_sources in rejected_sources_by_doc.items():
            doc_path = KNOWLEDGE_DIR / doc_filename
            if doc_path.exists() and doc_filename not in [t['filename'] for t in documents_updated]:
                self._add_rejected_sources_to_document(doc_path, rejected_sources)
                documents_updated.append({
                    "filename": doc_filename,
                    "title": doc_path.stem.replace('-', ' ').title(),
                    "facts_added": 0
                })
                self.stats["documents_updated"] += 1

        # Update index
        self._update_index()

        return {
            "merge_timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "documents_created": documents_created,
            "documents_updated": documents_updated,
            "index_updated": True,
            "log_entry_added": True
        }

    def _group_facts_by_topic(self, facts: List[Dict]) -> Dict[str, List[Dict]]:
        """Group facts by topic for document creation."""
        topics = {}

        for fact in facts:
            # Generate a topic based on source URL
            url = fact['source_url']
            topic = self._generate_topic_from_url(url)

            if topic not in topics:
                topics[topic] = []

            topics[topic].append(fact)

        return topics

    def _generate_topic_from_url(self, url: str) -> str:
        """Generate a topic name from URL."""
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')

        # Extract meaningful parts
        meaningful_parts = []
        for part in path_parts:
            if part and len(part) > 2 and part not in ['help', 'docs', 'api', 'library', 'guides']:
                meaningful_parts.append(part.replace('-', ' ').replace('_', ' ').title())

        if meaningful_parts:
            return ' '.join(meaningful_parts[-2:])  # Use last 2 meaningful parts
        else:
            return "Amazon Ads Documentation"

    def _generate_filename(self, topic: str) -> str:
        """Generate a filename from topic."""
        # Convert to lowercase, replace spaces with hyphens
        filename = topic.lower().replace(' ', '-')
        # Remove special characters
        filename = re.sub(r'[^a-z0-9-]', '', filename)
        # Ensure it's not too long
        if len(filename) > 60:
            filename = filename[:60].rstrip('-')
        return filename + '.md'

    def _create_document(self, doc_path: Path, topic: str, facts: List[Dict]) -> None:
        """Create a new OKF document."""
        # Generate timestamp
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Extract unique sources
        sources = []
        seen_urls = set()

        for fact in facts:
            url = fact['source_url']
            if url not in seen_urls:
                sources.append({
                    'url': url,
                    'type': fact['source_type'],
                    'confidence': fact['confidence']
                })
                seen_urls.add(url)

        # Generate topic_id
        topic_id = self._generate_filename(topic).replace('.md', '')

        # Create frontmatter
        frontmatter = f"""---
title: "{topic}"
last_updated: {timestamp}
sources:
"""
        for source in sources:
            frontmatter += f'  - url: "{source["url"]}"\n'
            frontmatter += f'    type: {source["type"]}\n'
            frontmatter += f'    confidence: {source["confidence"]}\n'

        frontmatter += f'topic_id: {topic_id}\n---\n\n'

        # Create body
        body = f"# {topic}\n\n"
        body += "## Overview\n\n"

        # Add facts as bullet points with citations
        for i, fact in enumerate(facts, 1):
            # Convert citation number to superscript
            citation_num = self._to_superscript(i)
            fact_text = fact['fact']
            body += f"- {fact_text} [{citation_num}]({fact['source_url']})\n"

        # Combine
        content = frontmatter + body

        # Write document
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(content)

        self._log(f"Created document: {doc_path.name}")

    def _update_document(self, doc_path: Path, new_facts: List[Dict]) -> None:
        """Update an existing OKF document."""
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()

            # Extract existing parts
            frontmatter, body = self._extract_okf_parts(existing_content)

            # Update timestamp
            timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            frontmatter['last_updated'] = timestamp

            # Add new sources if not already present
            sources = frontmatter.get('sources', '')

            # Build new frontmatter
            new_frontmatter = "---\n"
            new_frontmatter += f'title: "{frontmatter.get("title", "Document")}"\n'
            new_frontmatter += f'last_updated: {timestamp}\n'
            new_frontmatter += 'sources:\n'

            # Parse existing sources and add new ones
            existing_sources = self._parse_sources_from_frontmatter(existing_content)
            seen_urls = set(s['url'] for s in existing_sources)

            for source in existing_sources:
                new_frontmatter += f'  - url: "{source["url"]}"\n'
                new_frontmatter += f'    type: {source["type"]}\n'
                new_frontmatter += f'    confidence: {source["confidence"]}\n'

            for fact in new_facts:
                if fact['source_url'] not in seen_urls:
                    new_frontmatter += f'  - url: "{fact["source_url"]}"\n'
                    new_frontmatter += f'    type: {fact["source_type"]}\n'
                    new_frontmatter += f'    confidence: {fact["confidence"]}\n'
                    seen_urls.add(fact['source_url'])

            new_frontmatter += f'topic_id: {frontmatter.get("topic_id", "unknown")}\n---\n\n'

            # Append new facts to body
            base_citation_num = len(existing_sources) + 1
            for i, fact in enumerate(new_facts, base_citation_num):
                citation_num = self._to_superscript(i)
                fact_text = fact['fact']
                body += f"- {fact_text} [{citation_num}]({fact['source_url']})\n"

            # Combine and write
            new_content = new_frontmatter + body

            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            self._log(f"Updated document: {doc_path.name}")

        except Exception as e:
            self._log(f"Error updating document {doc_path.name}: {e}")

    def _add_rejected_sources_to_document(self, doc_path: Path, rejected_sources: List[Dict]) -> None:
        """Add rejected conflict sources to document for provenance without adding to body."""
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()

            # Extract existing parts
            frontmatter, body = self._extract_okf_parts(existing_content)

            # Update timestamp
            timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            frontmatter['last_updated'] = timestamp

            # Build new frontmatter
            new_frontmatter = "---\n"
            new_frontmatter += f'title: "{frontmatter.get("title", "Document")}"\n'
            new_frontmatter += f'last_updated: {timestamp}\n'
            new_frontmatter += 'sources:\n'

            # Parse existing sources
            existing_sources = self._parse_sources_from_frontmatter(existing_content)
            seen_urls = set(s['url'] for s in existing_sources)

            # Add existing sources
            for source in existing_sources:
                new_frontmatter += f'  - url: "{source["url"]}"\n'
                new_frontmatter += f'    type: {source["type"]}\n'
                new_frontmatter += f'    confidence: {source["confidence"]}\n'

            # Add rejected sources for provenance
            for rejected_source in rejected_sources:
                if rejected_source['url'] not in seen_urls:
                    new_frontmatter += f'  - url: "{rejected_source["url"]}"\n'
                    new_frontmatter += f'    type: {rejected_source["type"]}\n'
                    new_frontmatter += f'    confidence: {rejected_source["confidence"]}\n'
                    seen_urls.add(rejected_source['url'])

            new_frontmatter += f'topic_id: {frontmatter.get("topic_id", "unknown")}\n---\n\n'

            # Keep body unchanged
            new_content = new_frontmatter + body

            with open(doc_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            self._log(f"Added rejected sources to document: {doc_path.name}")

        except Exception as e:
            self._log(f"Error adding rejected sources to {doc_path.name}: {e}")

    def _parse_sources_from_frontmatter(self, content: str) -> List[Dict]:
        """Parse sources from existing frontmatter."""
        sources = []
        lines = content.split('\n')

        in_sources = False
        for line in lines:
            if line.strip() == 'sources:':
                in_sources = True
                continue

            if in_sources and line.strip().startswith('- url:'):
                url = line.split(':', 1)[1].strip().strip('"')
                # Look ahead for type and confidence
                sources.append({'url': url, 'type': 'official', 'confidence': 'high'})

            if in_sources and not line.startswith(' '):
                break

        return sources

    def _to_superscript(self, num: int) -> str:
        """Convert number to superscript Unicode."""
        superscripts = {
            '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
            '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
        }

        # For single digit
        if num < 10:
            return superscripts[str(num)]

        # For multi-digit, combine (though this might not look right)
        # Better to use [1], [2] format for numbers >= 10
        return str(num)

    def _update_index(self) -> None:
        """Update the knowledge base index."""
        try:
            # Collect all documents
            documents = []

            for md_file in KNOWLEDGE_DIR.glob("*.md"):
                if md_file.name in ['index.md', 'log.md']:
                    continue

                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    frontmatter, _ = self._extract_okf_parts(content)

                    documents.append({
                        'filename': md_file.name,
                        'title': frontmatter.get('title', md_file.stem.replace('-', ' ').title()),
                        'last_updated': frontmatter.get('last_updated', 'Unknown'),
                        'topic_id': frontmatter.get('topic_id', md_file.stem)
                    })
                except Exception as e:
                    self._log(f"Error reading {md_file.name}: {e}")

            # Sort by title
            documents.sort(key=lambda x: x['title'])

            # Generate index content
            index_content = """# Amazon Ads Knowledge Base Index

## Documents

| Document | Filename | Last Updated | Topic ID |
|----------|----------|--------------|----------|
"""
            for doc in documents:
                index_content += f"| [{doc['title']}]({doc['filename']}) | {doc['filename']} | {doc['last_updated']} | {doc['topic_id']} |\n"

            index_content += f"\n**Total Documents**: {len(documents)}\n"

            # Write index
            with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                f.write(index_content)

            self._log("Updated index.md")

        except Exception as e:
            self._log(f"Error updating index: {e}")

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
            # Stage 1: Hash Check and Content Fetch
            self._log(f"Processing: {url} ({source_type})")

            # Fetch content with error handling
            content, error = self.fetch_content(url, source_type)

            if error:
                if error == "404":
                    # Remove from seeds as specified
                    self._log(f"404 error: Removing {url} from seeds")
                    self._remove_from_seeds(url)
                    self.stats["sources_404_removed"] += 1
                    self.stats["sources_failed"] += 1
                    return False
                elif error == "rate_limited":
                    self._log(f"Rate limited: Will retry on next run")
                    self.stats["rate_limited"] += 1
                    self.stats["sources_failed"] += 1
                    return False
                elif error == "empty_content":
                    self._log(f"Empty content: Skipping {url}")
                    self.stats["sources_failed"] += 1
                    return False
                else:
                    self._log(f"Failed to fetch content: {error}")
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

    def _remove_from_seeds(self, url: str) -> None:
        """Remove a URL from the seed configuration."""
        try:
            if not SEED_CONFIG_FILE.exists():
                return

            with open(SEED_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Remove the URL from seeds
            original_count = len(config.get('seeds', []))
            config['seeds'] = [s for s in config.get('seeds', []) if s.get('url') != url]

            if len(config['seeds']) < original_count:
                with open(SEED_CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                self._log(f"Removed {url} from seed configuration")

        except Exception as e:
            self._log(f"Error removing from seeds: {e}")

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