#!/usr/bin/env node

/**
 * OKF Frontmatter Validation Script
 *
 * Validates that a file has proper OKF v0.1 frontmatter before allowing writes.
 * Called by PreToolUse hook for knowledge/ directory writes.
 *
 * Usage: node validate-okf.js <file_path>
 * Returns: 0 if valid, 1 if invalid
 */

const fs = require('fs');
const path = require('path');

// Get file path from command line argument
const filePath = process.argv[2];

// Check if file path was provided
if (!filePath) {
  console.error('Error: No file path provided');
  console.error('Usage: node validate-okf.js <file_path>');
  process.exit(1);
}

// Read file content
let fileContent;
try {
  fileContent = fs.readFileSync(filePath, 'utf8');
} catch (error) {
  console.error(`Error: Cannot read file '${filePath}': ${error.message}`);
  process.exit(1);
}

function validateOKFFrontmatter(content) {
  const errors = [];

  // Check for YAML frontmatter delimiters
  if (!content.startsWith('---')) {
    errors.push('Missing YAML frontmatter start delimiter (---)');
  }

  const frontmatterEnd = content.indexOf('---', 3);
  if (frontmatterEnd === -1) {
    errors.push('Missing YAML frontmatter end delimiter (---)');
    return errors;
  }

  // Extract frontmatter content
  const frontmatter = content.substring(3, frontmatterEnd).trim();

  // Parse frontmatter (simple line-by-line parsing)
  const lines = frontmatter.split('\n');
  const fields = {};

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    const colonPos = trimmed.indexOf(':');
    if (colonPos === -1) continue;

    const key = trimmed.substring(0, colonPos).trim();
    const value = trimmed.substring(colonPos + 1).trim();
    fields[key] = value;
  }

  // Validate required fields
  if (!fields.title) {
    errors.push('Missing required field: title');
  }

  if (!fields.last_updated) {
    errors.push('Missing required field: last_updated');
  } else {
    // Validate ISO 8601 date or timestamp format
    // Accepts both: YYYY-MM-DD and YYYY-MM-DDTHH:mm:ssZ
    const datePattern = /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$/;
    if (!datePattern.test(fields.last_updated.replace(/"/g, ''))) {
      errors.push('Invalid last_updated format (must be ISO 8601 date: YYYY-MM-DD or timestamp: YYYY-MM-DDTHH:mm:ssZ)');
    }
  }

  // Check for sources array
  if (!frontmatter.includes('sources:')) {
    errors.push('Missing required field: sources array');
  } else {
    // Validate sources array structure
    // Fixed: Allow other fields (like topic_id) to come after sources array
    // Fixed: Handle both Unix (\n) and Windows (\r\n) line endings
    const sourcesMatch = frontmatter.match(/sources:\s*\r?\n((?:\s*-\s*url:.*\r?\n\s*type:.*\r?\n\s*confidence:.*\r?\n?)+)/);
    if (!sourcesMatch) {
      errors.push('Invalid sources array format');
    } else {
      // Validate each source entry
      // Regex handles YAML indentation: optional leading whitespace on each line
      // Fixed: Handle both Unix (\n) and Windows (\r\n) line endings
      const sourceEntries = frontmatter.match(/-\s*url:\s*["']([^"']+)["']\s*\r?\n\s*type:\s*["']?(\w+)["']?\s*\r?\n\s*confidence:\s*["']?(\w+)["']?/g);
      if (!sourceEntries || sourceEntries.length === 0) {
        errors.push('Sources array must contain at least one source with url, type, and confidence');
      } else {
        sourceEntries.forEach(entry => {
          const urlMatch = entry.match(/url:\s*["']([^"']+)["']/);
          const typeMatch = entry.match(/type:\s*["']?(\w+)["']?/);
          const confMatch = entry.match(/confidence:\s*["']?(\w+)["']?/);

          if (!urlMatch || !urlMatch[1]) {
            errors.push('Source missing required field: url');
          }

          if (!typeMatch || !['official', 'community', 'blog'].includes(typeMatch[1])) {
            errors.push('Source type must be one of: official, community, blog');
          }

          if (!confMatch || !['high', 'medium', 'low'].includes(confMatch[1])) {
            errors.push('Source confidence must be one of: high, medium, low');
          }
        });
      }
    }
  }

  return errors;
}

function validateOKFBody(content, errors) {
  // Extract content body (after frontmatter)
  const frontmatterEnd = content.indexOf('---', 3);
  if (frontmatterEnd === -1) {
    // Already caught in frontmatter validation
    return;
  }

  const bodyStart = frontmatterEnd + 3; // Skip the closing '---'
  const body = content.substring(bodyStart).trim();

  // Check for content body
  if (!body || body.length === 0) {
    errors.push('Missing content body (document must have content after frontmatter)');
    return;
  }

  // Extract source URLs from frontmatter for citation validation
  const frontmatter = content.substring(3, frontmatterEnd).trim();
  const sourceUrls = [];
  const urlMatches = frontmatter.matchAll(/url:\s*["']([^"']+)["']/g);
  for (const match of urlMatches) {
    sourceUrls.push(match[1]);
  }

  // Validate citation format and URLs
  // Citations should use Unicode superscript format: [¹](url)
  const citationPattern = /\[¹\]\(([^)]+)\)/g;
  const invalidCitationPattern = /\[\d+\]\(([^)]+)\)/g; // Regular numbers [1], [2], etc.

  // Check for malformed citations (using regular numbers instead of superscript)
  const invalidMatches = body.matchAll(invalidCitationPattern);
  for (const match of invalidMatches) {
    errors.push('Invalid citation format: must use Unicode superscript [¹] not regular numbers [1], [2], etc.');
    break; // Only report once for this error type
  }

  // Check that all citation URLs are defined in sources
  const validMatches = body.matchAll(citationPattern);
  for (const match of validMatches) {
    const citationUrl = match[1];
    if (!sourceUrls.includes(citationUrl)) {
      errors.push(`Citation URL not defined in sources array: ${citationUrl}`);
    }
  }
}

// Run validation
const errors = validateOKFFrontmatter(fileContent);
validateOKFBody(fileContent, errors);

if (errors.length > 0) {
  // Output errors to stderr
  console.error('OKF Frontmatter Validation Failed:');
  errors.forEach(error => console.error('  - ' + error));
  process.exit(1);
} else {
  process.exit(0);
}
