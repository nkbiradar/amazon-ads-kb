# Design Document — Amazon Ads Knowledge Acquisition System

This covers both deliverables the brief asks for: system/agent architecture,
and design tradeoffs. It describes what's actually in this repo as of
2026-08-16, not an aspirational version of it.

## 1. Architecture

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

Four subagent definitions live in `.claude/agents/` (`scout`, `extractor`,
`validator`, `merger`); three skills in `.claude/skills/` define the OKF
format, dedup rules, and citation rules the agents and the deterministic code
both follow. `scripts/pipeline.py` invokes agents via `subprocess.run(["claude",
"--print", "--agent", name, "--agents", <custom-def-json>, "--output-format",
"json", "--json-schema", <schema>, prompt])` and parses the CLI's
`structured_output` envelope field. If an agent call fails or the batch is
too large for a single call, each stage has a documented deterministic
fallback — the pipeline never crashes because `claude` had a bad day, but it
also never claims agent-quality output when it used the fallback (every
fallback path calls `self._log(...)` explicitly).

## 2. The deterministic/fuzzy line, and why it's drawn where it is

The brief's framing is the actual design principle here: fetch, hash,
dedupe-by-URL, and file I/O are deterministic and testable, so they're plain
Python. Three genuinely fuzzy judgment calls are delegated to `claude`:

- **Extraction** — "is this sentence a fact about Amazon Ads, or marketing
  copy / navigation / JavaScript" is a judgment call, not a regex.
- **Validation** — "is this the same claim as an existing one, phrased
  differently, or a genuine conflict" needs semantic understanding, not just
  word overlap (the deterministic fallback approximates this with
  domain-term-overlap heuristics, which is why it only handles small batches
  as the primary path and is real about being an approximation for the rest).
- **Merger topic assignment** — "does this fact belong in an existing
  document or does it need a new one" is exactly the "5 sources describing
  Sponsored Products → one document" requirement from the brief. This is the
  one part of the original submission that was actively wrong: the merger
  agent was invoked, its result was thrown away, and a URL-parsing heuristic
  (`_generate_topic_from_url`) decided document boundaries instead — which is
  how the knowledge base ended up with `products-amazon-dsp.md` and
  `amazon-dsp-demand-side-platform.md` as two separate documents about the
  same product. Fixed 2026-08-16: the merger agent's topic assignment is now
  what `_execute_merger_operations` actually groups facts by; the URL
  heuristic is now only the fallback when the agent call fails.

Everything else — writing OKF frontmatter, computing SHA-256 content hashes,
deciding whether a fact passes OKF validation, running the PreToolUse hook —
is deterministic on purpose, because those are the parts that need to be
provably correct and re-run-safe, and "provably correct" is much cheaper to
get from unit tests than from a model call.

## 3. Known limitations (honest notes, per the brief's own ask)

- **Scout is the weakest stage.** It doesn't discover new sources — it
  verifies the one seed URL it's given and returns it. Real source discovery
  (crawling a docs site, or using a search MCP as the brief suggests) isn't
  implemented. For a seed-list-driven pipeline this is a real gap, not a
  cosmetic one.
- **The deterministic validation fallback is an approximation.** Word/domain-
  term overlap (`_classify_fact_relationship`) is a reasonable heuristic for
  catching near-duplicates, but it will miss semantically-identical facts
  phrased very differently, and can false-positive on facts that share
  vocabulary but aren't actually the same claim. The agent path (≤5 facts per
  batch) is the intended primary path for exactly this reason.
- **No end-to-end run with a live, authenticated `claude` and open network
  access has been captured in this repo yet.** The fixes made 2026-08-16 were
  verified in a sandbox with neither (see `RUN.md`'s verification section for
  exactly what was and wasn't confirmed). Whoever runs this next should
  capture that transcript in `RUN.md`.
- **13 of the 26 committed knowledge documents were near-duplicates** sharing
  a source URL with another document (sometimes a locale variant of the same
  guide), and were consolidated 2026-08-16 — see `knowledge/index.md` for the
  removed filenames and what happened to their content. Two were placeholder
  documents that described their own prior corruption rather than containing
  Amazon Ads facts, and one was raw GitHub page chrome captured as a fact.
  These existed because the original fetch fallback (`fetch_content`) dropped
  to `response.text[:5000]` — raw, unstripped HTML/JS — whenever structured
  tag extraction came up short. That fallback now uses `soup.get_text()`
  instead (still script/style-stripped), so this specific failure mode
  shouldn't recur, but it's worth spot-checking new documents after a run.
- **`advertising.amazon.com/help/*` and `/API/docs/*` cannot be fetched by
  this pipeline at all.** Confirmed by fetching them directly: they return a
  client-side-rendered app shell (a tracking pixel and `title: Amazon`, no
  body content) because the real page renders via JavaScript after load.
  `fetch_content()` uses plain `requests`, which never executes JS, so this
  isn't fixable without a headless-browser fetcher (Playwright, as the brief
  itself suggested). `/library/guides/*` and `/solutions/products/*` URLs
  are real server-rendered HTML and work fine — the three broken seeds are
  disabled in `sources/seed-urls.json` with a note explaining why, rather
  than left in as silent, guaranteed failures.
- **This is a prototype, not a production system.** No retry queue for
  MCP/agent-call failures beyond the fetch layer's retries, no concurrency,
  no monitoring. That's an intentional scope choice given the brief's own
  "You Don't Need: production-ready code" — flagging it so it isn't confused
  for an oversight.

## 4. What I'd improve next, if this kept going

1. Give Scout an actual search/crawl capability so the system can find
   sources on its own, not just verify ones it's handed.
2. Extend the validator agent's json_schema so the fuzzy conflict-detection
   path also runs on large batches instead of falling back to heuristics —
   probably by chunking rather than an arbitrary 5-fact cutoff.
3. A "why was this fact rejected/merged/skipped" audit trail per source run,
   surfaced somewhere more visible than grepping `knowledge/log.md`.
4. Automated CI (even a simple GitHub Action running
   `test_okf_validation.py` and the error-handling suite on every push) so a
   regression like the PyYAML datetime crash in `test_okf_validation.py`
   gets caught before it sits unnoticed.

## 5. How Claude Code was used

Four project-specific subagents (`.claude/agents/*.md`) define the prompts
and JSON schemas for extraction, validation, and merge-topic-assignment;
`scripts/pipeline.py` calls them via the CLI (`claude -p ... --agent ...
--agents ... --output-format json --json-schema ...`) rather than delegating
the whole task to one open-ended Claude Code session — the intent being that
each stage's contract (input shape, output schema, fallback behavior) is
explicit and testable independently of what any specific model call returns.
The PreToolUse hook (`scripts/validate-okf.js`, wired in
`.claude/settings.json`) is the one place Claude Code enforces something
regardless of what any agent or fallback path produces: a file under
`knowledge/` missing the `type` field (OKF v0.1's one hard requirement)
cannot be written, full stop, independent of which code path tried to write
it.

*(Note on this document's own history: earlier verification reports in this
repo — `TASK_1`/`TASK_5`/`TASK_6`/`TASK_7`/`TASK_8_*_REPORT.md` — claimed
things that weren't true when checked (e.g. "26/26 tests passing" when
`test_okf_validation.py` in fact crashed with a `TypeError` on every real
document). Those files are left in the repo for the record but shouldn't be
read as verified; `RUN.md`'s verification section is the current source of
truth for what's actually been confirmed.)*
