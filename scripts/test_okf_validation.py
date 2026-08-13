#!/usr/bin/env python3
"""
OKF (Open Knowledge Format) Validation Script

Validates all markdown files in the knowledge/ directory for OKF compliance:
- Required frontmatter fields (title, last_updated, sources with url/type/confidence)
- At least one inline citation in the body
- Non-empty file content
"""

import os
import sys
import re
from pathlib import Path
from datetime import datetime
import json

class OKFValidator:
    def __init__(self, knowledge_dir="knowledge/"):
        self.knowledge_dir = Path(knowledge_dir)
        self.results = []
        self.passed = 0
        self.failed = 0

    def is_excluded_file(self, filename):
        """Check if file should be excluded from validation"""
        excluded = ["index.md", "log.md"]
        return filename in excluded

    def extract_frontmatter(self, content):
        """Extract YAML frontmatter from markdown content"""
        lines = content.split('\n')

        # Find frontmatter boundaries
        if not lines or lines[0] != '---':
            return None, content

        frontmatter_end = -1
        for i, line in enumerate(lines[1:], 1):
            if line == '---':
                frontmatter_end = i
                break

        if frontmatter_end == -1:
            return None, content

        frontmatter_text = '\n'.join(lines[1:frontmatter_end])
        body_content = '\n'.join(lines[frontmatter_end+1:])

        return frontmatter_text, body_content

    def parse_frontmatter(self, frontmatter_text):
        """Parse YAML frontmatter into dictionary"""
        if not frontmatter_text:
            return None

        try:
            import yaml
            return yaml.safe_load(frontmatter_text)
        except ImportError:
            # Fallback: simple YAML parsing for our specific format
            return self.simple_yaml_parse(frontmatter_text)

    def simple_yaml_parse(self, text):
        """Simple YAML parser for OKF frontmatter format"""
        data = {}
        lines = text.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                i += 1
                continue

            # Top-level key (no leading whitespace)
            if ':' in line and not line.startswith(' '):
                parts = line.split(':', 1)
                key = parts[0].strip()

                # Check if there's a value (might be empty for nested structures)
                if len(parts) > 1:
                    value = parts[1].strip().strip('"\'')
                else:
                    value = ''

                # Check if next line starts a list (or if value is empty suggesting nested structure)
                if i + 1 < len(lines) and (not value or lines[i + 1].strip().startswith('- ')):
                    next_line = lines[i + 1].strip()
                    if next_line.startswith('- '):
                        data[key] = []
                        current_list = key
                        current_dict = None
                        i += 1

                        # Process list items
                        while i < len(lines):
                            list_line = lines[i]

                            # New list item
                            if list_line.strip().startswith('- '):
                                new_dict = {}
                                data[key].append(new_dict)
                                current_dict = new_dict

                                # Parse key-value on same line
                                item_text = list_line.strip()[2:]  # Remove '- '
                                if ': ' in item_text:
                                    item_parts = item_text.split(': ', 1)
                                    item_key = item_parts[0].strip()
                                    item_value = item_parts[1].strip().strip('"\'')
                                    current_dict[item_key] = item_value

                            # Nested property (with extra indentation)
                            elif list_line.startswith('  ') and ': ' in list_line and current_dict is not None:
                                nested_parts = list_line.strip().split(': ', 1)
                                nested_key = nested_parts[0].strip()
                                nested_value = nested_parts[1].strip().strip('"\'')

                                # Handle list values
                                if nested_value.startswith('[') and nested_value.endswith(']'):
                                    # Simple list parsing
                                    nested_value = nested_value[1:-1].split(',')
                                    nested_value = [v.strip().strip('"\'') for v in nested_value]

                                current_dict[nested_key] = nested_value
                            else:
                                # End of list
                                break

                            i += 1
                        continue  # Skip the increment at the end
                    else:
                        data[key] = value
                else:
                    data[key] = value
                i += 1
            else:
                i += 1

        return data

    def validate_frontmatter(self, frontmatter_data, filename):
        """Validate required frontmatter fields"""
        errors = []

        if not frontmatter_data:
            errors.append("Missing frontmatter section")
            return errors

        # Check required fields
        required_fields = ['title', 'last_updated', 'type', 'sources']
        for field in required_fields:
            if field not in frontmatter_data or not frontmatter_data[field]:
                errors.append(f"Missing required field: {field}")

        # Validate document-level type field
        if 'type' in frontmatter_data:
            type_value = str(frontmatter_data['type']).strip().strip('"\'')
            if not type_value:
                errors.append("Document-level type field cannot be empty")

        # Validate last_updated format (ISO 8601)
        if 'last_updated' in frontmatter_data:
            try:
                datetime.fromisoformat(frontmatter_data['last_updated'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                errors.append(f"Invalid last_updated format: {frontmatter_data['last_updated']}")

        # Validate sources structure
        if 'sources' in frontmatter_data:
            sources = frontmatter_data['sources']
            if not isinstance(sources, list) or len(sources) == 0:
                errors.append("Sources must be a non-empty list")
            else:
                for i, source in enumerate(sources):
                    if not isinstance(source, dict):
                        errors.append(f"Source {i+1}: must be a dictionary")
                        continue

                    # Check required source fields
                    required_source_fields = ['url', 'type', 'confidence']
                    for field in required_source_fields:
                        if field not in source or not source[field]:
                            errors.append(f"Source {i+1}: missing field '{field}'")

                    # Validate confidence values
                    if 'confidence' in source:
                        valid_confidence = ['high', 'medium', 'low']
                        if source['confidence'] not in valid_confidence:
                            errors.append(f"Source {i+1}: invalid confidence value '{source['confidence']}'")

                    # Validate type values
                    if 'type' in source:
                        valid_types = ['official', 'community', 'blog']
                        if source['type'] not in valid_types:
                            errors.append(f"Source {i+1}: invalid type value '{source['type']}'")

        return errors

    def validate_citations(self, body_content):
        """Check for inline citations in body content"""
        # Match various citation formats including Unicode superscripts
        citation_patterns = [
            r'\[[⁰¹²³⁴⁵⁶⁷⁸⁹]+]\([^)]+\)',   # Unicode superscript citations like [¹](url)
            r'\[\d+\]\([^)]+\)',          # Numeric citations like [1](url)
            r'\[citation\:\d+\]\([^)]+\)' # citation:N format
        ]

        citations = []
        for pattern in citation_patterns:
            citations.extend(re.findall(pattern, body_content))

        if not citations:
            return ["No inline citations found in body content"]

        return []

    def validate_file(self, filepath):
        """Validate a single OKF file"""
        filename = filepath.name

        if self.is_excluded_file(filename):
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {
                'file': filename,
                'status': 'FAIL',
                'errors': [f"Could not read file: {e}"]
            }

        # Check if file is empty
        if not content.strip():
            return {
                'file': filename,
                'status': 'FAIL',
                'errors': ["File is empty"]
            }

        errors = []

        # Extract and validate frontmatter
        frontmatter_text, body_content = self.extract_frontmatter(content)
        frontmatter_data = self.parse_frontmatter(frontmatter_text)

        # Validate frontmatter structure
        frontmatter_errors = self.validate_frontmatter(frontmatter_data, filename)
        errors.extend(frontmatter_errors)

        # Validate citations (only if frontmatter is valid)
        if not frontmatter_errors:
            citation_errors = self.validate_citations(body_content)
            errors.extend(citation_errors)

        if errors:
            return {
                'file': filename,
                'status': 'FAIL',
                'errors': errors
            }
        else:
            return {
                'file': filename,
                'status': 'PASS',
                'errors': []
            }

    def run_validation(self):
        """Run validation on all markdown files in knowledge directory"""
        print("[*] OKF Validation Test")
        print("=" * 60)
        print(f"Scanning: {self.knowledge_dir}")
        print()

        if not self.knowledge_dir.exists():
            print(f"[!] Knowledge directory not found: {self.knowledge_dir}")
            return False

        md_files = list(self.knowledge_dir.glob("*.md"))
        print(f"Found {len(md_files)} markdown files")
        print()

        for filepath in sorted(md_files):
            result = self.validate_file(filepath)
            if result:
                self.results.append(result)

                if result['status'] == 'PASS':
                    self.passed += 1
                    print(f"[PASS] {result['file']}")
                else:
                    self.failed += 1
                    print(f"[FAIL] {result['file']}")
                    for error in result['errors']:
                        print(f"   - {error}")

        print()
        print("=" * 60)
        print("[*] Results Summary")
        print(f"Total files tested: {len(self.results)}")
        print(f"[PASS] Passed: {self.passed}")
        print(f"[FAIL] Failed: {self.failed}")
        print(f"Success rate: {(self.passed/len(self.results)*100):.1f}%")

        return self.failed == 0

def run_regression_tests():
    """Run regression tests for document-level type field validation"""
    print("[*] OKF Document-Level Type Regression Tests")
    print("=" * 60)

    # Test 1: Valid document with type field should PASS
    print("\nTest 1: Valid document with type:knowledge field")
    valid_doc = """---
title: "Test Document"
last_updated: "2026-08-14T12:00:00Z"
type: knowledge
sources:
  - url: "https://advertising.amazon.com/help"
    type: official
    confidence: high
topic_id: test-document
---

# Test Document

Test content with citation [¹](https://advertising.amazon.com/help).
"""

    validator = OKFValidator()
    frontmatter, body = validator.extract_frontmatter(valid_doc)
    frontmatter_data = validator.parse_frontmatter(frontmatter)
    errors = validator.validate_frontmatter(frontmatter_data, "test_valid.md")

    if errors:
        print(f"[FAIL] Valid document rejected (should PASS): {errors}")
    else:
        print(f"[PASS] Valid document accepted correctly")

    # Test 2: Document missing type field should FAIL
    print("\nTest 2: Document missing type field")
    invalid_doc = """---
title: "Test Document"
last_updated: "2026-08-14T12:00:00Z"
sources:
  - url: "https://advertising.amazon.com/help"
    type: official
    confidence: high
topic_id: test-document
---

# Test Document

Test content with citation [¹](https://advertising.amazon.com/help).
"""

    validator2 = OKFValidator()
    frontmatter2, body2 = validator2.extract_frontmatter(invalid_doc)
    frontmatter_data2 = validator2.parse_frontmatter(frontmatter2)
    errors2 = validator2.validate_frontmatter(frontmatter_data2, "test_invalid.md")

    if errors2 and any('Missing required field: type' in error for error in errors2):
        print(f"[PASS] Document missing type rejected correctly")
    else:
        print(f"[FAIL] Document missing type should be rejected but wasn't")

    # Test 3: Document with empty type field should FAIL
    print("\nTest 3: Document with empty type field")
    empty_type_doc = """---
title: "Test Document"
last_updated: "2026-08-14T12:00:00Z"
type: ""
sources:
  - url: "https://advertising.amazon.com/help"
    type: official
    confidence: high
topic_id: test-document
---

# Test Document

Test content with citation [¹](https://advertising.amazon.com/help).
"""

    validator3 = OKFValidator()
    frontmatter3, body3 = validator3.extract_frontmatter(empty_type_doc)
    frontmatter_data3 = validator3.parse_frontmatter(frontmatter3)
    errors3 = validator3.validate_frontmatter(frontmatter_data3, "test_empty.md")

    if errors3 and any('cannot be empty' in error for error in errors3):
        print(f"[PASS] Document with empty type rejected correctly")
    else:
        print(f"[FAIL] Document with empty type should be rejected but wasn't")

    print()
    print("=" * 60)
    print("Regression tests completed")

def main():
    # First run regression tests
    run_regression_tests()
    print()

    # Then run full validation suite
    validator = OKFValidator()
    success = validator.run_validation()

    print()
    if success:
        print("[SUCCESS] All OKF documents passed validation!")
        return 0
    else:
        print("[WARNING] Some documents failed validation")
        return 1

if __name__ == "__main__":
    sys.exit(main())