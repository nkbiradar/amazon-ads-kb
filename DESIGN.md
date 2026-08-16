# Design Document — Amazon Ads Knowledge Acquisition System

Tradeoffs and why, known limitations, what would come next, and how Claude
Code was used. (The high-level design, component/subagent responsibilities,
data flow, and tech choices are in `ARCHITECTURE.md` — that document is the
"what," this one's the "why.") Describes what's actually in this repo as of
2026-08-17, not an aspirational version of it.

## 1. The deterministic/fuzzy line, and why it's drawn where it is

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

## 2. Known limitations (honest notes, per the brief's own ask)

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
- **The extractor and merger agent calls fail on this project's current
  environment** with `401 Authentication Error, Invalid proxy server token
  passed` — the `litellm.retap.ai` proxy token used to route `claude` to a
  non-Anthropic model is invalid/expired. Confirmed via a real live run
  2026-08-16 once error logging was fixed to surface the actual message
  (previously truncated before reaching it). This is an environment
  credential issue, not a code bug — both stages correctly fell back to
  their deterministic paths instead of crashing. See `RUN.md` for the full
  error text and what refreshing the token would unlock.
- **A real, complete end-to-end run was captured 2026-08-16.** First attempt
  crashed with `Error processing ...: 'last_checked'` despite 8 valid facts
  extracted (`Documents created: 0`) — `_fallback_validation` dropped the
  `last_checked` field when reshaping facts, and `_create_document` read it
  via unsafe `fact[...]` indexing instead of `.get()`. Fixed, reproduced the
  exact failing sequence in isolation to confirm, then re-ran live: completed
  cleanly, `knowledge/basics-of-amazon-attribution.md` created with 8 real
  cited facts, passes `test_okf_validation.py`. That same run also exposed a
  second real bug — `documents_created`/`documents_updated` counters were
  incremented twice (once inside the merger functions, once by their
  caller), so 1 real document was reported as 2. Fixed and verified with a
  standalone repro. See `RUN.md`'s verification section for the full
  transcript and both fixes.
- **13 of the original 26 committed knowledge documents were near-duplicates**
  sharing a source URL with another document (sometimes a locale variant of
  the same guide), and were consolidated 2026-08-16, bringing the count to
  13 — see `knowledge/index.md` for the removed filenames and what happened
  to their content. Two were placeholder documents that described their own
  prior corruption rather than containing Amazon Ads facts, and one was raw
  GitHub page chrome captured as a fact. These existed because the original
  fetch fallback (`fetch_content`) dropped to `response.text[:5000]` — raw,
  unstripped HTML/JS — whenever structured tag extraction came up short.
  That fallback now uses `soup.get_text()` instead (still script/style-
  stripped), so this specific failure mode shouldn't recur, but it's worth
  spot-checking new documents after a run. A 14th document
  (`basics-of-amazon-attribution.md`) was added back later the same day by
  a real, live pipeline run against that URL (see `RUN.md`), so the current
  count is 14, still under the 15-document cap.
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

## 3. What I'd improve next, if this kept going

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

## 4. How Claude Code was used

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
