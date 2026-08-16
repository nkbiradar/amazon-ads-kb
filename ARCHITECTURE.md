# System & Agent Architecture — Amazon Ads Knowledge Acquisition System

High-level design, component/subagent responsibilities, data flow, and tech
choices. (Tradeoffs, limitations, and how Claude Code was used day-to-day
are in `DESIGN.md` — this document is the "what," that one's the "why.")

## 1. High-level design

The system is a five-stage pipeline — Discover → Extract → Validate → Merge
→ Publish — orchestrated by `scripts/pipeline.py` (`PipelineOrchestrator`),
with the fuzzy stages delegated to `claude` subagents and the deterministic
stages handled directly in Python.

```
sources/seed-urls.json
        │
        ▼
scripts/pipeline.py (PipelineOrchestrator)
        │
   ┌────┴─────────────────────────────────────────────┐
   │  per source, in process_source():                │
   │                                                    │
   │  1. Hash check (deterministic — hash_check.py)    │
   │     skip if unchanged → re-run safety             │
   │                                                    │
   │  2. Fetch (deterministic — requests + BeautifulSoup)│
   │     strip script/style/nav, extract p/h/li/td text │
   │                                                    │
   │  3. Extract (fuzzy — claude --agent extractor)     │
   │     .claude/agents/extractor.md defines the rules  │
   │     falls back to keyword-line matching on failure │
   │                                                    │
   │  4. Validate (fuzzy — claude --agent validator,    │
   │     ≤5 facts; deterministic word/domain-term        │
   │     overlap for larger batches)                    │
   │     .claude/agents/validator.md                    │
   │                                                    │
   │  5. Merge — topic assignment is fuzzy (claude       │
   │     --agent merger decides which document a fact    │
   │     belongs to), the actual write is deterministic  │
   │     (_create_document/_update_document in Python)   │
   │                                                    │
   └────┬─────────────────────────────────────────────┘
        ▼
knowledge/*.md (OKF v0.1) + index.md + log.md
        ▲
        │ PreToolUse hook (.claude/settings.json →
        │ scripts/validate-okf.js) blocks any Write/Edit
        │ to knowledge/*.md missing required frontmatter
```

## 2. Component & subagent responsibilities

**`scripts/pipeline.py` (`PipelineOrchestrator`)** — the orchestrator. Owns
the source loop, hash checking, fetching, stats tracking, log/index writing,
and invoking each subagent via the `claude` CLI. Nothing in this file makes
a judgment call about what a fact *means* — it moves data between stages and
writes the deterministic parts (frontmatter, hashes, file I/O) itself.

**Scout** (`.claude/agents/scout.md`) — given a seed URL, verifies it's
reachable and categorizes its source type (official/community/blog). Tools:
`playwright`, `search`, `WebSearch`. Narrowest role of the four agents by
design — see `DESIGN.md`'s limitations section for why this is the weakest
stage as implemented.

**Extractor** (`.claude/agents/extractor.md`) — given fetched page content,
returns discrete factual claims as structured JSON (`facts: [{fact,
source_url, source_type, confidence}]`), rejecting marketing copy,
navigation text, JavaScript, and terms-of-service boilerplate. No tools —
pure text-in, JSON-out.

**Validator** (`.claude/agents/validator.md`) — given new facts and read
access to `knowledge/` (tools: `Glob`, `Grep`, `Read`), classifies each fact
as new, a duplicate, or a conflict against existing documents, resolving
conflicts by source-confidence hierarchy (official > community > blog).
Runs for batches of ≤5 facts; larger batches use a deterministic
word/domain-term-overlap fallback (see `DESIGN.md`).

**Merger** (`.claude/agents/merger.md`) — given validated facts and the list
of existing `knowledge/` document titles, decides *only* which filename each
fact belongs to (existing document or a new one) — explicitly `tools: []`,
no file access. `scripts/pipeline.py` does the actual write
(`_execute_merger_operations`) based on that assignment. This split exists
so the OKF-format-compliance and re-run-safety guarantees don't depend on
what a model call happens to produce — see this agent's own file for the
"why this agent only assigns topics, not files" note.

**Skills** (`.claude/skills/`) — `okf-format.md`, `dedup-rules.md`,
`citation-rules.md` define the format, deduplication, and citation rules
that both the agents' prompts and the deterministic Python code follow, so
there's one source of truth for "what counts as valid" rather than two
independently-drifting implementations.

**Hook** (`.claude/settings.json` → `scripts/validate-okf.js`) — a
`PreToolUse` hook on `Write`/`Edit` matched to `knowledge/*.md`. Reads the
tool invocation JSON from stdin, checks required frontmatter fields
(`title`, `last_updated`, `type`, `sources`), and exits with code `2` plus a
JSON denial reason to block a non-conforming write — regardless of whether
the write came from the pipeline's code, a fallback path, or a human typing
into Claude Code directly.

## 3. Data flow

1. `sources/seed-urls.json` (or a single `--url` CLI arg) is the entry
   point.
2. Each URL goes through `_run_hash_check()` — SHA-256 over
   whitespace-normalized fetched text, compared against
   `sources/sources.json`. Unchanged → skip, nothing else runs for that
   source.
3. Changed/new content flows into `invoke_extractor_agent()`, which calls
   `claude --print --agent extractor --agents <def> --output-format json
   --json-schema <schema>` via `subprocess.run`, parses the
   `structured_output` envelope field, and falls back to deterministic
   keyword-line extraction on any failure (logged explicitly either way).
4. Extracted facts flow into `invoke_validator_agent()` (agent path for
   ≤5 facts, deterministic overlap-scoring fallback otherwise), producing a
   per-fact status: `new`, `duplicate`, `conflict-resolved`, or
   `conflict-rejected`.
5. `new`/`conflict-resolved` facts flow into `invoke_merger_agent()`, which
   asks the merger agent for topic assignments, then
   `_execute_merger_operations()` groups facts by assigned filename and
   calls `_create_document()`/`_update_document()` — the only place OKF
   markdown actually gets written.
6. Every write to `knowledge/*.md` passes through the `PreToolUse` hook
   first. `_update_index()` and `_write_summary()` regenerate
   `knowledge/index.md` and append to `knowledge/log.md` at the end of each
   run.

## 4. Tech choices

- **Plain Python + `requests`/`BeautifulSoup4` for fetching**, not an MCP
  server. Simpler to test and debug for this assignment's scope; the
  tradeoff (can't render `advertising.amazon.com/help/*`'s client-side JS)
  is documented in `DESIGN.md` rather than hidden.
- **`claude` invoked via `subprocess` with `--agents <custom-json>`**
  (ad-hoc agent definitions passed inline) rather than only the committed
  `.claude/agents/*.md` files, so each call's model/tools/schema is
  explicit and independently testable — `--output-format json
  --json-schema <schema>` gives a `structured_output` field to parse
  instead of scraping free text.
- **OKF v0.1 as plain Markdown + YAML frontmatter** — human-readable,
  diffable in `git`, and the one hard rule (`type` field) is cheap to
  enforce with a hook rather than a heavier validation service.
- **SHA-256 content hashing over normalized text** for change detection —
  simple, deterministic, testable without a live model call, and the
  correct primitive for "run it twice, only real changes apply."
- **Node for the validation hook, Python for everything else** — matches
  what each does natively: `scripts/validate-okf.js` is exactly what
  Claude Code's `PreToolUse` hook contract expects (a small script reading
  stdin JSON, exiting 0/2), while the orchestration, fetching, and
  subprocess management are more naturally Python.

See `DESIGN.md` for the reasoning behind the deterministic/fuzzy split
itself, known limitations, what would come next, and how Claude Code was
used to build and debug this.
