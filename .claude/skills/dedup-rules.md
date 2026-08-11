---
description: Deduplication rules for Amazon Ads knowledge base. Defines how to match facts to existing topics, detect duplicates vs new facts vs conflicts, and use content hashing for exact duplicate detection.
---

# Deduplication Rules

## Topic Matching Rules

### Determine if Fact Belongs to Existing Document

Given a new fact and existing documents in `knowledge/`, determine if the fact belongs to an existing topic or requires a new document.

**Step 1: Check topic_id Similarity**

If the fact comes from validation report with `related_document` field:
- Use that document as the primary target
- Skip to fact-level deduplication

If no `related_document` specified:

**Step 2: Title and Content Similarity**

Compare fact content against existing document titles and bodies:

```python
# Pseudo-code for topic matching
existing_docs = glob("knowledge/*.md")

for doc in existing_docs:
    title_similarity = compare(fact_keywords, doc.title)
    content_overlap = count_overlapping_terms(fact, doc.content)
    
    if title_similarity > 0.7 OR content_overlap > 3:
        # Strong match - use this document
        target_doc = doc
        break
```

**Matching Thresholds:**
- **Title similarity > 70%**: Same topic (e.g., "Budget Limits" vs "Budgeting")
- **Content overlap ≥ 3 terms**: Related topic if terms are domain-specific (e.g., "campaign", "budget", "bidding" all appearing in both)
- **Both below thresholds**: New topic - create new document

**Topic Keywords to Consider:**
- Campaign types: sponsored-products, sponsored-brands, sponsored-display
- Features: budget, bidding, targeting, keywords, products
- Technical: api, endpoint, authentication, oauth, limits
- Performance: reporting, metrics, attribution, conversions

### When to Create New Document

Create new document when:
- Fact covers a topic not present in existing documents
- Fact is substantively different from all existing topics
- Fact would create an unfocused document if merged (e.g., mixing API and UI topics)

## Fact-Level Deduplication

### Detect Exact Duplicates

Use content hashing for exact duplicate detection:

```python
# Generate normalized hash for comparison
def fact_hash(fact_text):
    # Normalize: lowercase, trim, remove extra whitespace
    normalized = " ".join(fact_text.lower().split())
    return sha256(normalized.encode()).hexdigest()
```

**Exact Duplicate Rules:**
Two facts are exact duplicates if:
1. Their content hashes are identical, OR
2. Text is identical after normalizing (case, whitespace)

**Action: Mark as `duplicate`** - Do not add to document

### Detect Near-Duplicates (Semantic Duplicates)

Two facts are semantic duplicates if they:
- Have different wording but identical meaning
- Describe the same concept with minor syntactic differences
- Are paraphrases of each other

**Semantic Duplicate Examples:**
```
Fact 1: "Daily budgets for Sponsored Products must be at least $1.00"
Fact 2: "Sponsored Products campaigns require a minimum daily budget of $1"
→ Semantic duplicate - same meaning, different wording
```

**Detection Method:**
Compare key information elements:
- Entity (Sponsored Products)
- Attribute (daily budget minimum)
- Value ($1.00/$1)

**Action: Mark as `duplicate`** - Do not add to document

### Detect Conflicts

Two facts conflict if they:
- Make contradictory claims about the same topic
- Provide different values for the same parameter
- State mutually exclusive capabilities

**Conflict Examples:**
```
Fact 1: "Daily budgets for Sponsored Products must be at least $1.00"
Fact 2: "Sponsored Products campaigns require a minimum daily budget of $10.00"
→ Conflict: different minimum values
```

```
Fact 1: "Amazon Ads API supports OAuth 2.0 authentication"
Fact 2: "Amazon Ads API only supports API key authentication"
→ Conflict: mutually exclusive authentication methods
```

**Detection Method:**
- Extract subject, predicate, and object from each fact
- Compare predicates and objects for same subject
- Flag contradictions (different values for same attribute)

**Action: Mark as `conflict-resolved` or `conflict-rejected`**
- Apply confidence hierarchy: official > community > blog
- Higher confidence wins, lower is rejected

### Detect New Facts

A fact is new if it:
- Has no exact or semantic duplicate in existing documents
- Does not conflict with existing facts
- Adds information not previously documented

**Action: Mark as `new`** - Add to document

## Deduplication Workflow

```python
def deduplicate_fact(new_fact, existing_document):
    # Step 1: Check exact duplicates
    for existing_fact in existing_document.facts:
        if fact_hash(new_fact.text) == fact_hash(existing_fact.text):
            return "duplicate"
    
    # Step 2: Check semantic duplicates
    for existing_fact in existing_document.facts:
        if is_semantic_duplicate(new_fact, existing_fact):
            return "duplicate"
    
    # Step 3: Check conflicts
    for existing_fact in existing_document.facts:
        if is_conflict(new_fact, existing_fact):
            if new_fact.confidence > existing_fact.confidence:
                return "conflict-resolved"
            else:
                return "conflict-rejected"
    
    # Step 4: Must be new
    return "new"
```

## Content Hashing Implementation

### Hash Format

Use SHA-256 hashes for fact deduplication:

```python
import hashlib

def generate_fact_hash(fact_text):
    """
    Generate normalized hash for fact deduplication.
    
    Normalization steps:
    1. Convert to lowercase
    2. Trim leading/trailing whitespace
    3. Remove extra internal whitespace
    4. Remove punctuation (optional, depends on strictness)
    """
    normalized = " ".join(fact_text.lower().strip().split())
    return hashlib.sha256(normalized.encode()).hexdigest()
```

**Example:**
```
Original: "Daily budgets must be at least $1.00"
Normalized: "daily budgets must be at least $1.00"
Hash: "a3f5e8b2c1d4..."
```

### Hash Storage

Store fact hashes in document metadata for future comparison:

```yaml
---
title: "Budget Limits"
fact_hashes:
  - "a3f5e8b2c1d4..." # "Daily budgets must be at least $1.00"
  - "b4f6e9c3d2e5..." # "Maximum budget is $1,000,000"
---
```

## Semantic Comparison Rules

### Key Information Extraction

Extract structured components for comparison:

**Fact Pattern: "Subject + Predicate + Object"**
```
"Sponsored Products campaigns require a minimum daily budget of $1.00"
→ Subject: Sponsored Products campaigns
→ Predicate: require minimum daily budget
→ Object: $1.00
```

**Compare Components:**
- Subjects similar? (campaign type match)
- Predicates similar? (attribute type match)
- Objects different? (conflict detection)

### Paraphrase Detection

Facts are semantic duplicates if all key components match with variations in:
- Word order (active vs passive voice)
- Synonyms (require vs need vs must)
- Phrasing (at least vs minimum vs minimum of)

**Semantic Match Examples:**
```
✅ Same meaning:
- "Campaigns require a minimum daily budget"
- "Daily budget minimum is required"
- "Minimum daily budget requirement"

❌ Different meaning:
- "Campaigns require a minimum daily budget"
- "Campaigns have no maximum budget limit"
```

## Conflict Resolution Hierarchy

### Confidence-Based Resolution

When conflicts are detected, resolve by source confidence:

```
official (high) > community (medium) > blog (low)
```

**Resolution Rules:**
1. Compare confidence levels of conflicting facts
2. Higher confidence fact wins
3. Lower confidence fact is rejected
4. If equal confidence, keep existing (stability preference)

**Examples:**
```
Existing: "Minimum budget is $10" (blog, low confidence)
New: "Minimum budget is $1" (official, high confidence)
→ New wins (high > low)

Existing: "Minimum budget is $1" (official, high confidence)
New: "Minimum budget is $5" (official, high confidence)
→ Existing wins (stability, equal confidence)
```

## Implementation Notes

### Performance Considerations

- Cache fact hashes for existing documents
- Use hash lookups for exact duplicate checks (O(1))
- Use semantic comparison only when hashes don't match
- Group facts by topic before comparison

### Edge Cases

**Numeric Variations:**
- "$1" vs "$1.00" vs "1 USD" → Same value (duplicate)
- "1000" vs "1,000" vs "1k" → Same value (duplicate)
- "1.0" vs "1.5" → Different values (conflict)

**Temporal Changes:**
- Fact values may change over time
- Always trust latest official source
- Note deprecated facts in document

**Source Conflicts:**
- Same source may publish conflicting information
- Use most recent publication date
- Note discrepancy if dates unclear
