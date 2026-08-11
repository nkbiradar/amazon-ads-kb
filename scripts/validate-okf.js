#!/usr/bin/env node

/**
 * OKF Frontmatter Validation Script
 *
 * Validates that a file has proper OKF v0.1 frontmatter before allowing writes.
 * Called by PreToolUse hook for knowledge/ directory writes.
 *
 * Usage: node validate-okf.js <file_content>
 * Returns: 0 if valid, 1 if invalid
 */

const fs = require('fs');

// Get file content from command line argument
const fileContent = process.argv[2] || '';

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
    // Validate ISO 8601 timestamp format
    const isoPattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
    if (!isoPattern.test(fields.last_updated.replace(/"/g, ''))) {
      errors.push('Invalid last_updated format (must be ISO 8601: YYYY-MM-DDTHH:mm:ssZ)');
    }
  }

  // Check for sources array
  if (!frontmatter.includes('sources:')) {
    errors.push('Missing required field: sources array');
  } else {
    // Validate sources array structure
    const sourcesMatch = frontmatter.match(/sources:\s*\n((?:\s*-\s*url:.*\n(?:\s*type:.*\n(?:\s*confidence:.*\n)?)?)+)/);
    if (!sourcesMatch) {
      errors.push('Invalid sources array format');
    } else {
      // Validate each source entry
      const sourceEntries = frontmatter.match(/-\s*url:\s*["']([^"']+)["']\s*\ntype:\s*(\w+)\s*\nconfidence:\s*(\w+)/g);
      if (!sourceEntries || sourceEntries.length === 0) {
        errors.push('Sources array must contain at least one source with url, type, and confidence');
      } else {
        sourceEntries.forEach(entry => {
          const urlMatch = entry.match(/url:\s*["']([^"']+)["']/);
          const typeMatch = entry.match(/type:\s*(\w+)/);
          const confMatch = entry.match(/confidence:\s*(\w+)/);

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

// Run validation
const errors = validateOKFFrontmatter(fileContent);

if (errors.length > 0) {
  // Output errors to stderr
  console.error('OKF Frontmatter Validation Failed:');
  errors.forEach(error => console.error('  - ' + error));
  process.exit(1);
} else {
  process.exit(0);
}
