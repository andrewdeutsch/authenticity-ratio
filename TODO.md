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

---

## Score Multiplier Transparency & Calibration

**Priority**: High  
**Context**: Coherence and Verification scores receive automatic 25-30% boosts for marketing content, which can mask underlying quality issues and prevent actionable feedback from being surfaced to users.

**Current Behavior**:
- Coherence: `base_score * 1.25` for landing pages, product pages, and "other" content
- Verification: `base_score * 1.30` for landing pages, product pages, and "other" content
- Rationale: "LLM applies overly strict editorial standards to marketing content"
- Issue: Base scores of ~75% become 95-100%, triggering "improvement opportunity" mode where LLM often returns empty suggestions

**Related Files**:
- `scoring/scorer.py:247-256` - Verification multiplier
- `scoring/scorer.py:457-461` - Coherence multiplier
- Commit: `40caa0c` (Nov 19, 2025)

**Options to Address**:

1. **Make Multipliers Configurable**
   - Move hardcoded `1.25` and `1.30` to `config/rubric.yaml`
   - Add per-dimension multiplier settings with content-type conditions
   - Allow users to disable multipliers or set custom values
   - Document rationale for default values
   - Effort: 2-3 hours

2. **Add Detailed Score Logging**
   - Log base LLM scores separately from adjusted scores
   - Show both in debug output and reports
   - Add "Score Breakdown" section showing base, multiplier, and final
   - Track multiplier impact in analytics
   - Effort: 3-4 hours

3. **Create Multiplier Calibration Tool**
   - Build script to test different multiplier values (1.0-1.4)
   - Compare against human-labeled "ground truth" scores
   - Analyze impact on score distribution and feedback generation
   - Document optimal multiplier values with evidence
   - Effort: 6-8 hours

4. **Remove/Reduce Multipliers**
   - Test removing multipliers entirely (set to 1.0)
   - Evaluate if LLM is actually "too strict" or appropriately critical
   - Consider reducing multipliers (e.g., 1.10 instead of 1.25)
   - Compare feedback quality with vs without multipliers
   - Effort: 2-3 hours

5. **Improve LLM Prompts Instead**
   - Rather than boosting scores, adjust prompts to be content-type aware
   - Add explicit guidance: "This is marketing content, apply marketing standards"
   - Test if better prompts eliminate need for multipliers
   - Measure prompt effectiveness vs score adjustments
   - Effort: 4-6 hours

6. **Make Improvement Opportunities Mandatory**
   - For scores ≥90%, require at least ONE improvement suggestion
   - Update prompt at `scorer.py:846` to mandate suggestions
   - Change from "return empty array if excellent" to "always provide micro-optimizations"
   - Ensure users always understand "why not 100%?"
   - Effort: 1-2 hours

7. **Adjust Feedback Threshold**
   - Current: `score < 0.9` triggers "issues" mode, `≥0.9` triggers "improvements" mode
   - Options:
     - Lower to 0.95 (only 95%+ gets improvement mode)
     - Remove distinction (always ask for issues + improvements)
     - Add third tier: <0.7 = issues, 0.7-0.95 = improvements, >0.95 = validation
   - Test which threshold produces most actionable feedback
   - Effort: 2-3 hours

8. **Separate Base & Adjusted Scores in UI**
   - Show users both "Raw LLM Score" and "Adjusted Score"
   - Explain why adjustment was applied
   - Let users toggle between views
   - Add tooltip: "Adjusted for marketing content standards"
   - Effort: 3-4 hours

**Success Metrics**:
- Users understand why they got their score (even at 95-100%)
- Feedback is always actionable and specific
- Score adjustments are transparent and justified
- False positive rate for "issues" is minimized

**Quick Wins** (Start Here):
1. Add logging (Option 2) - Low effort, high visibility
2. Make configurable (Option 1) - Enables experimentation
3. Mandate improvements (Option 6) - Immediate UX improvement

**Diagnostic Tool**: Run `python scripts/diagnose_high_scores.py` to analyze score adjustments

**Total Estimated Effort**: 2-8 hours depending on option(s) chosen