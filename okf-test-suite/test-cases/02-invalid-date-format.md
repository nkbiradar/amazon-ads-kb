---
title: "Invalid Date Format Test"
last_updated: "08/11/2026"
sources:
  - url: "https://advertising.amazon.com/help"
    type: "official"
    confidence: "high"
---

# Test Document

This document has `last_updated` in MM/DD/YYYY format instead of ISO 8601 (YYYY-MM-DD).
It should FAIL frontmatter validation.

Some content here with a citation[¹](https://advertising.amazon.com/help).
