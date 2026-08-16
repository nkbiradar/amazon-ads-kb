#!/usr/bin/env node

/**
 * OKF Frontmatter Validation Script
 *
 * Validates that a file has proper OKF v0.1 frontmatter before allowing writes.
 * Called by PreToolUse hook for knowledge/ directory writes.
 *
 * Reads tool invocation JSON from stdin:
 * {
 *   "tool_name": "Write" | "Edit",
 *   "tool_input": {
 *     "file_path": "...",
 *     "content": "...",  // for Write
 *     "new_string": "..."  // for Edit
 *   }
 * }
 *
 * Returns: 0 if valid, 2 if invalid (blocks the tool call)
 */

const fs = require('fs');
const path = require('path');

// Read tool invocation from stdin
let toolInvocation;
try {
  const stdinBuffer = fs.readFileSync(0, 'utf-8'); // Read from stdin (fd 0)
  toolInvocation = JSON.parse(stdinBuffer);
} catch (error) {
  console.error('Error: Cannot read tool invocation from stdin:', error.message);
  process.exit(1);
}

// Extract content based on tool type
let fileContent;
const toolName = toolInvocation.toolName || toolInvocation.tool_name;
const toolInput = toolInvocation.toolInput || toolInvocation.tool_input;

if (toolName === 'Write') {
  fileContent = toolInput.content;
} else if (toolName === 'Edit') {
  fileContent = toolInput.new_string;
} else {
  console.error(`Error: Unexpected tool name: ${toolName}`);
  console.error('Input received:', JSON.stringify(toolInvocation, null, 2));
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

    // Skip array items (lines starting with '-') and nested properties (indented lines)
    if (trimmed.startsWith('-')) continue;
    if (line !== line.trimLeft()) continue; // Skip indented lines (nested properties)

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

  // Validate document-level type field
  if (!fields.type) {
    errors.push('Missing required field: type');
  } else {
    // Remove quotes and check if empty
    const typeValue = fields.type.replace(/"/g, '').trim();
    if (!typeValue) {
      errors.push('Document-level type field cannot be empty');
    }
    // Accept any non-empty value for now (knowledge, guide, reference, etc.)
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
  // Output JSON decision to deny the tool use
  const errorOutput = {
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: 'OKF frontmatter validation failed: ' + errors.join('; ')
    },
    systemMessage: 'OKF validation failed. Document must have valid frontmatter with: title, last_updated, type, and sources array.'
  };

  console.log(JSON.stringify(errorOutput, null, 2));
  process.exit(2); // Exit code 2 blocks the tool call
} else {
  // Allow the tool use (exit 0 means no decision, normal permission flow applies)
  process.exit(0);
}
