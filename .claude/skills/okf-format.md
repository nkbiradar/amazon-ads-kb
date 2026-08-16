---
description: OKF v0.1 format specification for Amazon Ads knowledge base documents. Defines required YAML frontmatter fields, markdown body structure, and provides a complete example document.
---

# OKF v0.1 Format Specification

## Required Frontmatter Fields

Every OKF document MUST begin with YAML frontmatter containing these fields:

```yaml
---
title: "Document Title"
last_updated: 2026-06-18T12:00:00Z
type: knowledge
sources:
  - url: "https://..."
    type: official|community|blog
    confidence: high|medium|low
topic_id: unique-topic-slug
---
```

### Field Specifications

**title**: Document title
- Type: String
- Required: Yes
- Format: Descriptive, human-readable title
- Example: `"Sponsored Products Campaign Management"`

**last_updated**: ISO 8601 timestamp
- Type: String (ISO 8601 format)
- Required: Yes
- Format: `YYYY-MM-DDTHH:mm:ssZ`
- Updates on every change to the document

**type**: Document-level type
- Type: String
- Required: Yes — **this is OKF v0.1's one hard rule.** `scripts/validate-okf.js`
  (the PreToolUse hook) rejects any write to `knowledge/*.md` that's missing
  this field, full stop, regardless of how good the rest of the document is.
- Value: The pipeline always writes `knowledge`; the validator accepts any
  non-empty string, but use `knowledge` unless you have a specific reason not to.

**sources**: Array of source objects
- Type: Array of objects
- Required: Yes
- Each source MUST contain:
  - `url`: Full URL to source
  - `type`: One of `official`, `community`, or `blog`
  - `confidence`: One of `high`, `medium`, or `low`

**topic_id**: Unique topic identifier
- Type: String (kebab-case)
- Required: Yes
- Format: lowercase-with-hyphens
- Must be unique across all documents
- Used for cross-references and deduplication

## Markdown Body Structure

### Section Organization

Body MUST be organized with hierarchical sections:

```markdown
# Main Title (matches title field)

## Overview
High-level description of the topic.

## Key Concepts
Explanations of core concepts and terminology.

## Features and Capabilities
Detailed feature descriptions.

## Technical Details
### API Information
Endpoint, parameter, and response details.

### Configuration
Settings, options, and configuration parameters.

## Limitations and Constraints
Known limitations and restrictions.

## Related Topics
Links to related documents in the knowledge base.
```

### Inline Citations

Every factual statement MUST include an inline citation:

```markdown
Amazon Ads supports sponsored products, brands, and display campaigns. [¹](https://advertising.amazon.com/docs)

Daily budgets for Sponsored Products must be at least $1.00. [²](https://advertising.amazon.com/api-reference)
```

**Citation Format:**
- Superscript number: `[¹]`, `[²]`, `[³]`, etc.
- Parenthetical link to source URL
- Number corresponds to position in `sources` array (1-indexed)
- Multiple facts from same source reuse the same citation number

## Complete Example Document

```markdown
---
title: "Sponsored Products Campaign Management"
last_updated: 2026-06-18T15:30:00Z
type: knowledge
sources:
  - url: "https://advertising.amazon.com/API/docs/v2/guides/sponsored-products"
    type: official
    confidence: high
  - url: "https://github.com/amazon/amazon-ads-api-samples"
    type: community
    confidence: medium
  - url: "https://blog.example.com/amazon-ads-guide"
    type: blog
    confidence: low
topic_id: sponsored-products-campaigns
---

# Sponsored Products Campaign Management

## Overview

Sponsored Products are ads that appear in Amazon search results and product pages. [¹](https://advertising.amazon.com/API/docs/v2/guides/sponsored-products)

## Campaign Structure

Sponsored Products campaigns use a hierarchical structure with three levels:

1. **Campaign** - Top level container with budget and schedule settings
2. **Ad Group** - Group of ads with targeting and bidding settings
3. **Keywords/Products** - Individual targeting items with bid amounts [¹](https://advertising.amazon.com/API/docs/v2/guides/sponsored-products)

## Budget Requirements

Daily budgets must meet minimum requirements:
- Minimum daily budget: $1.00 [¹](https://advertising.amazon.com/API/docs/v2/guides/sponsored-products)
- Budgets can be set at campaign level only
- No maximum budget limit

## Bidding Strategies

Amazon Ads supports multiple bidding strategies:

- **Automatic Bidding**: Amazon optimizes bids for clicks or conversions
- **Manual Bidding**: Advertiser sets fixed bid amounts [²](https://github.com/amazon/amazon-ads-api-samples)

Note: Some blog posts suggest additional strategies, but only automatic and manual are officially documented. [³](https://blog.example.com/amazon-ads-guide)

## Targeting Options

### Keyword Targeting
- Match types: Broad, Phrase, Exact
- Negative keywords supported
- Bid adjustments by match type

### Product Targeting
- Target specific products or categories
- Product attribute filtering
- Negative product targeting [¹](https://advertising.amazon.com/API/docs/v2/guides/sponsored-products)

## API Integration

The Amazon Ads API provides endpoints for:
- Campaign creation and management
- Budget modification
- Keyword and product targeting
- Performance reporting [²](https://github.com/amazon/amazon-ads-api-samples)

## Limitations

Known constraints for Sponsored Products:
- Maximum 1000 active keywords per ad group
- Campaign name maximum 128 characters
- Daily budget changes may take up to 24 hours to take effect [¹](https://advertising.amazon.com/API/docs/v2/guides/sponsored-products)

## Related Topics

- [Budget Limits](budget-limits.md)
- [API Authentication](api-authentication.md)
- [Performance Reporting](performance-reporting.md)
```

## Implementation Checklist

When creating or updating OKF documents:

- [ ] All required frontmatter fields present, including `type` (non-empty — the hook blocks the write otherwise)
- [ ] `last_updated` is current ISO timestamp
- [ ] `sources` array has no duplicate URLs
- [ ] `topic_id` is unique and kebab-case
- [ ] Title in frontmatter matches # heading in body
- [ ] Every factual statement has inline citation
- [ ] Citation numbers match sources array positions
- [ ] Sections follow hierarchical structure
- [ ] Markdown is valid and properly formatted
- [ ] Cross-references to related topics included
