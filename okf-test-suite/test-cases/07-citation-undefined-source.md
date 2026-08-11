---
title: "Citation Undefined Source Test"
last_updated: "2026-08-11"
sources:
  - url: "https://advertising.amazon.com/help"
    type: "official"
    confidence: "high"
---

# Test Document

This document has an inline citation pointing to a URL that is NOT
listed in the frontmatter `sources` array.
It should FAIL citation validation.

Some content here with a citation[¹](https://some-random-untracked-domain.com/page).
