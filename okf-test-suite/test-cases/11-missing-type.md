---
title: "Missing Type Document"
last_updated: "2026-08-11"
sources:
  - url: "https://advertising.amazon.com/help"
    type: "official"
    confidence: "high"
---

# Missing Type Document

Everything else about this document is valid OKF — title, last_updated, and a
proper sources array. It should FAIL validation for exactly one reason: it has
no document-level `type` field. This isolates the type-field rule (OKF v0.1's
one hard requirement) from every other check, so a pass here can't be masking
a missing-type bug the way it could when every other broken test case also
happened to be missing type.

Amazon Ads supports several campaign types[¹](https://advertising.amazon.com/help).
