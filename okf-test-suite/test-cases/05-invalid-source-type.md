---
title: "Invalid Source Type Test"
last_updated: "2026-08-11"
sources:
  - url: "https://advertising.amazon.com/help"
    type: "third-party"
    confidence: "high"
---

# Test Document

The source `type` field is set to "third-party", which is not one of the
allowed values (official/community/blog).
It should FAIL source validation.

Some content here with a citation[¹](https://advertising.amazon.com/help).
