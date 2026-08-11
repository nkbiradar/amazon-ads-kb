---
description: Citation and attribution rules for Amazon Ads knowledge base. Defines inline citation format, confidence scoring based on source type, and how to handle conflicting sources with clear notation.
---

# Citation Rules

## Inline Citation Format

### Basic Citation Structure

Every factual statement MUST include an inline citation using superscript numbers:

```markdown
Amazon Ads supports sponsored products, brands, and display campaigns. [¹](https://advertising.amazon.com/docs)
```

**Citation Components:**
- Superscript number: `[¹]`, `[²]`, `[³]`, etc.
- Parenthetical Markdown link to source URL
- Number corresponds to position in document's `sources` array (1-indexed)

### Citation Number Assignment

Citation numbers are assigned based on the `sources` array in document frontmatter:

```yaml
---
sources:
  - url: "https://advertising.amazon.com/docs"        # → [¹]
  - url: "https://github.com/amazon/amazon-ads-sdk"  # → [²]
  - url: "https://blog.example.com/amazon-ads"       # → [³]
---
```

**Assignment Rules:**
- First source = `[¹]`, second source = `[²]`, etc.
- Same URL always gets same citation number
- Multiple facts from same source reuse same citation number

### Multiple Citation Examples

```markdown
## Budget Requirements
Daily budgets for Sponsored Products must be at least $1.00. [¹](https://advertising.amazon.com/docs)

Maximum budget limits vary by campaign type and account status. [¹](https://advertising.amazon.com/docs) [²](https://github.com/amazon/amazon-ads-sdk)
```

When multiple sources support the same fact, list all citations:
```markdown
Amazon Ads API supports OAuth 2.0 authentication. [¹](https://advertising.amazon.com/docs) [²](https://github.com/amazon/amazon-ads-sdk)
```

### Citation Placement Rules

**Place citations:**
- At the end of the factual statement
- After punctuation (period, comma)
- Before section headings if the citation applies to the entire section

```markdown
✅ Correct:
Sponsored Products campaigns require a minimum daily budget of $1.00. [¹](https://...)

❌ Incorrect:
Sponsored Products campaigns [¹](https://...) require a minimum daily budget of $1.00.
```

## Confidence Scoring Rules

### Source Type to Confidence Mapping

Assign confidence levels based on source type:

```
official → high
community → medium  
blog → low
```

**Source Type Definitions:**
- **official**: Amazon Ads official documentation, API reference, help docs
- **community**: GitHub repositories, code samples, SDK implementations
- **blog**: Blog posts, tutorials, third-party articles

### Confidence Application

When attributing facts, always include the confidence level:

```yaml
sources:
  - url: "https://advertising.amazon.com/api-reference"
    type: official
    confidence: high
```

**Confidence determines:**
- Source precedence in conflicts
- Trust level for fact validation
- Priority when merging information

### Confidence Escalation

Confidence can be upgraded based on corroboration:

```python
# Confidence escalation rules
if fact.confidence == "low":
    if corroborated_by_official_source(fact):
        fact.confidence = "high"
    elif corroborated_by_multiple_community_sources(fact, count=3):
        fact.confidence = "medium"
```

**Escalation Examples:**
- Blog post fact confirmed by official docs → Upgrade to high
- Blog post fact confirmed by 3+ GitHub repos → Upgrade to medium
- Never downgrade confidence (once high, stays high)

## Conflict Attribution

### When Sources Disagree

When multiple sources provide conflicting information, attribute ALL sources and indicate which was used:

```markdown
Daily budget minimums for Sponsored Products vary by source:
- Official documentation states $1.00 minimum [¹](https://advertising.amazon.com/docs)
- Some tutorials suggest $10.00 minimum [²](https://blog.example.com/amazon-ads)
- Used official documentation (higher confidence)
```

### Conflict Notation Format

Use this format for conflicts:

```markdown
**Note:** [Source A] states [Fact A], but [Source B] states [Fact B]. [Source B] used due to [higher confidence/more recent/official source].
```

**Examples:**

```markdown
**Note:** Blog posts suggest a minimum daily budget of $10.00 for Sponsored Products [²], but official documentation states $1.00 [¹]. Official documentation used (higher confidence).

**Note:** Older GitHub examples show API v1 endpoints [²], but current documentation recommends v2 [¹]. API v2 used (current version).

**Note:** Some community sources suggest API key authentication [²], but official documentation only supports OAuth 2.0 [¹]. OAuth 2.0 used (official source).
```

### Multiple Conflicts Resolution

When multiple conflicts exist, format as a table:

```markdown
## Conflicting Information

| Attribute | Community Sources | Official Sources | Used | Reason |
|-----------|-------------------|------------------|------|---------|
| Budget minimum | $10.00 [²] | $1.00 [¹] | $1.00 | Official docs |
| API version | v1 [²] | v2 [¹] | v2 | Current version |
| Auth method | API key [²] | OAuth 2.0 [¹] | OAuth 2.0 | Official docs |
```

## Source Combination Rules

### Same Fact, Multiple Sources

When multiple independent sources agree on a fact, cite all of them:

```markdown
Amazon Ads API supports sponsored products, sponsored brands, and sponsored display campaigns. [¹](https://advertising.amazon.com/docs) [²](https://github.com/amazon/amazon-ads-sdk) [³](https://developer.amazon.com/docs)
```

**Combination increases confidence:**
- Single source → Base confidence
- 2+ independent sources → Increased confidence
- Official + community agreement → Highest confidence

### Redundant Sources

Don't cite redundant sources (same source, different URLs):

```markdown
✅ Correct:
Official documentation confirms OAuth 2.0 support. [¹](https://advertising.amazon.com/docs)

❌ Incorrect:
Official documentation confirms OAuth 2.0 support. [¹](https://advertising.amazon.com/docs) [²](https://advertising.amazon.com/docs/oauth) [³](https://advertising.amazon.com/api-auth)
```

**Rule:** One citation per unique source, even if multiple URLs

## Special Citation Cases

### Derivative Facts

When combining multiple facts into a new conclusion, cite all contributing sources:

```markdown
Based on official documentation, Sponsored Products campaigns require both a minimum daily budget of $1.00 and at least one targeting keyword. [¹](https://advertising.amazon.com/docs) [²](https://advertising.amazon.com/targeting)
```

### Quoted Content

When directly quoting source content, use block quotes and cite:

```markdown
> Sponsored Products are keyword- or product-targeted ads that appear in shopping results and product pages.
> 
> — [Amazon Ads Official Documentation](https://advertising.amazon.com/docs) [¹]
```

### Undocumented Features

When features exist but aren't officially documented, note clearly:

```markdown
**Note:** The API accepts an optional `retry_count` parameter, but this is not documented in official specifications. [²](https://github.com/amazon/amazon-ads-sdk) Community source only.
```

## Citation Maintenance

### Updating Citations

When updating documents:
- Add new sources to `sources` array
- Assign new citation numbers sequentially
- Update existing citations if source positions change
- Preserve citation numbers for unchanged sources

### Removing Citations

When removing outdated information:
- Remove fact and its citation
- Remove source from `sources` array if no longer referenced
- Renumber remaining citations if needed
- Note removal in change log

### Source Validation

Before citing a source, verify:
- URL is accessible and valid
- Content actually supports the cited fact
- Source is current (not deprecated)
- Source type is correctly classified

## Citation Quality Rules

### Required Citations

Every factual statement requires a citation. These require citations:

```markdown
✅ Needs citation:
- API endpoint URLs and parameters
- Budget limits and requirements  
- Feature capabilities and options
- Configuration settings and defaults
- Authentication methods
- Performance metrics and limits
```

### Optional Citations

These types of content may not require citations:

```markdown
❌ No citation needed:
- Obvious organizational statements (e.g., "This document covers...")
- Navigation and structural elements
- Common knowledge (e.g., "APIs require authentication")
- Editorial transitions (e.g., "Next, we'll discuss...")
```

### Over-Citation Avoidance

Don't cite every sentence in a paragraph. Group related facts:

```markdown
✅ Efficient:
Amazon Ads API supports sponsored products, brands, and display campaigns. All campaign types require OAuth 2.0 authentication and support both automatic and manual bidding strategies. [¹](https://advertising.amazon.com/docs)

❌ Excessive:
Amazon Ads API supports sponsored products. [¹](https://advertising.amazon.com/docs) It also supports sponsored brands. [¹](https://advertising.amazon.com/docs) And display campaigns. [¹](https://advertising.amazon.com/docs) All require OAuth 2.0. [¹](https://advertising.amazon.com/docs) They support bidding. [¹](https://advertising.amazon.com/docs)
```

## Implementation Checklist

When creating or updating documents:

- [ ] Every factual statement has inline citation
- [ ] Citation numbers match `sources` array positions
- [ ] Same source URL gets same citation number
- [ ] Confidence levels assigned correctly by source type
- [ ] Conflicts noted with clear attribution
- [ ] Multiple independent sources cited when available
- [ ] Redundant sources avoided
- [ ] Derivative conclusions cite all contributing sources
- [ ] Undocumented features clearly marked as such
- [ ] URLs are valid and accessible
