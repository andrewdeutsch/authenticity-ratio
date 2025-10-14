Two-stage scoring: triage + high-quality

Goal

Implement a two-stage scoring pipeline to reduce expensive LLM calls while preserving scoring quality.

Motivation

Current approach: the scorer sends one OpenAI call per content item. In runs with many items this creates high cost and latency. A lightweight triage stage will filter obvious inauthentic or obviously irrelevant items so the high-quality model only scores the ambiguous subset.

Acceptance criteria

- A new, optional feature flag (env var or config) enables two-stage scoring.
- Implementation of a cheap "triage" model (can use an inexpensive LLM, a simpler prompt, or a rules-based heuristic) that processes content in batches and outputs one of: "skip" (no further scoring), "needs_scoring".
- The high-quality scorer processes only items labeled "needs_scoring".
- Unit tests that mock model endpoints to validate behavior:
  - triage filters correctly (skip vs needs_scoring)
  - high-quality scorer invoked only for the filtered subset
- Benchmark script that runs: per-item single-model vs two-stage approach on a synthetic dataset and prints call counts and wall-clock time.
- Documentation in README/TODO explaining trade-offs and how to enable the feature.

Design notes

- The triage model can be initially implemented as a simple rule set (e.g., short content, presence of official handles, verified domains) to keep cost at zero while we iterate.
- Later we can add a small dedicated LLM (cheaper model) for triage to improve recall.
- Batching: triage should support batching (e.g., 16 items per request) to lower overhead.
- Metrics: record number of triage calls, high-quality calls, and resulting AR to compare.

Implementation steps

1. Add feature flag to `config/settings.py` (e.g., `USE_TRIAGE_SCORING`).
2. Implement `scoring/triage.py` with a `TriageScorer` that supports a simple rules-based mode and a placeholder LLM mode.
3. Update `scoring/ContentScorer` to run triage first when the flag is enabled and only call the expensive scorer for items that pass.
4. Add unit tests under `tests/test_trige_scoring.py` (mock both triage and high-quality calls).
5. Add `scripts/benchmark_scoring.py` to compare approaches.
6. Update README and TODO.

Notes on incremental rollout

- Start with rules-based triage to get immediate cost savings.
- Add logging/metrics and a "dry-run" mode where triage decisions are logged but not applied, to compare distributions before switching.

Estimated effort: 3–6 hours (rules-based triage + tests + benchmark).