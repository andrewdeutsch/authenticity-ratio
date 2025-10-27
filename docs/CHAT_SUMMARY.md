Project: authenticity-ratio
Date: 2025-10-23

Summary
-------
This document captures the recent assistant session that hardened Brave ingestion, added a Playwright opt-in fallback (respecting robots.txt), and improved reporting (concise per-item diagnostics and more reliable Appendix heuristics).

Goals implemented
- Harden Brave ingestion: prefer Brave API when key present; fallback to HTML scraping on API errors; retries, headers, OG meta extraction, and raw HTML debug dumps implemented.
- Playwright opt-in fallback: headful rendering is opt-in via env var `BRAVE_USE_PLAYWRIGHT`; Playwright renders are only used after robots.txt allows the user-agent and when HTTP fetches fail or return thin content.
- Robots.txt: module-level robots.txt cache `_ROBOTS_CACHE` and `_is_allowed_by_robots(url, user_agent)` ensures we respect robots across fetches.
- Footer extraction: `_extract_footer_links(html, base_url)` added to capture Terms/Privacy links at fetch time and stored in `NormalizedContent.meta['terms']` and `['privacy']`.
- Pipeline wiring: `collect_brave_pages()` added and wired into `scripts/run_pipeline.py` so Brave collection yields N usable pages (skip robots-disallowed and thin pages).
- Reporting: extractive summarizer added in `reporting/markdown_generator.py` (short 2-line descriptions). Executive examples and Appendix item descriptions can now be produced by an LLM (default: GPT-3.5-turbo) when enabled via the run flags `--use-llm-examples` / `--llm-model` or when report data sets `use_llm_for_descriptions`/`use_llm_for_examples`. LLM-generated descriptions are labeled in the report with the model name. Appendix heuristics (explicit Title bullet, noisy-snippet detection, body-scan fallback for Terms/Privacy) remain in place as a fallback.
- Metadata propagation: footer links propagate from `NormalizedContent.meta` to `ContentScores.meta` so reports receive per-item footer links.

Important files touched
- `ingestion/brave_search.py`: search_brave(), fetch_page(), _extract_footer_links(), collect_brave_pages(), _is_allowed_by_robots().
- `scripts/run_pipeline.py`: wired Brave collector and added CLI flags `--use-llm-examples` and `--llm-model`; `NormalizedContent.meta` now includes `terms`/`privacy`.
- `reporting/markdown_generator.py`: extractive summarizer, `_llm_summarize()` hook (uses GPT-3.5-turbo by default), appendix heuristics, and term/privacy fallback scanning. The appendix and executive examples will use the LLM when `use_llm_for_examples` or `use_llm_for_descriptions` is enabled; generated summaries are annotated with the LLM model name.
- `scoring/scorer.py`: propagate `terms`/`privacy` into `ContentScores.meta`.
- `tests/test_footer_detection.py`: new unit tests for `_extract_footer_links()`.

Environment & run notes
- Python: 3.11 (used for runs in this session).
- Playwright: required only if `BRAVE_USE_PLAYWRIGHT=1`; install browsers with `playwright install`.
- Important env vars:
  - `BRAVE_USE_PLAYWRIGHT=1` — enable Playwright fallback (opt-in)
  - `BRAVE_ALLOW_HTML_FALLBACK=1` — allow HTML scraping fallback when API errors
  - `AR_FETCH_DEBUG_DIR` — directory to write raw HTML dumps for debugging
  - `BRAVE_API_KEY`, `BRAVE_API_ENDPOINT` — Brave API credentials and endpoint

Representative run command
--------------------------
(uses zsh)

BRAVE_USE_PLAYWRIGHT=1 BRAVE_ALLOW_HTML_FALLBACK=1 AR_FETCH_DEBUG_DIR=/tmp/ar_fetch_debug \
python3.11 scripts/run_pipeline.py --brand-id footer-test --keywords "openai" --sources brave \
--brave-pages 3 --max-content 10 --output-dir output/runs/run_footer_test --log-level INFO

Tests added
- `tests/test_footer_detection.py` — unit tests for `_extract_footer_links()` (passed during development).

Next recommended tasks
- Add unit tests that exercise `fetch_page()` end-to-end using mocks for HTTP and Playwright to ensure `terms`/`privacy` keys are always present in return values.
- Add tests for summarizer heuristics and Appendix rules in `reporting/markdown_generator.py`.
- Decide whether to keep the body-scan fallback in Appendix once ingestion proves reliable; if not, remove it and rely on ingestion metadata exclusively.

Notes for future assistants
- When starting a new chat, read this file and then open the files referenced above to see current code and tests.
- The key design intent: prefer non-intrusive scraping first (API -> HTTP) and only render pages headfully when permitted by robots and when necessary. Preserve raw HTML for debugging and propagate footer metadata through the pipeline.

Contact if unclear
- If you need the exact diffs or a chronological list of commits, ask and I'll add an abbreviated changelog or patch set.

## Final run review (2025-10-24)

During a final validation run (`run_final_run` for brand `final-test`) the pipeline collected 3 Brave results (Playwright-enabled fallback), scored and classified them, and generated a Markdown/PDF report at `output/runs/run_final_run`. The report was reviewed and annotated with per-item description quality, key issues, and prioritized fixes so future assistant sessions can pick up the same remediation work quickly.

Summary verdict
--------------
- Pipeline: Robust; API→HTML→Playwright fallbacks behaved as expected and footer metadata propagated through normalization and scoring.
- Report: Actionable (ARs, visuals, classifications). Per-item descriptions are mixed: one item contained noisy/gibberish snippets, others were mostly fine but slightly longer than the two-line target.
- Recommended immediate focus: improve extractive summarizer to prefer article/long-paragraph content and aggressively filter UI/noise snippets.

Per-item ratings (brief)
-----------------------
- OpenAI — Label: Inauthentic (45.8)
  - Clarity: 1.5/5 — description contains noisy/unrelated fragments.
  - Concision: 2/5 — truncated and incoherent.
  - Accuracy: 2/5 — label may be defensible but description doesn't support it.

- API Platform | OpenAI — Label: Authentic (76.8)
  - Clarity: 4/5 — meaningful description of API/compliance signals.
  - Concision: 3.5/5 — slightly over target but useful.
  - Accuracy: 4/5 — supports the label.

- Sora | OpenAI — Label: Suspect (60.8)
  - Clarity: 4/5 — good functional summary.
  - Concision: 3.5/5 — slightly over target.
  - Accuracy: 3.5/5 — reasonably aligned with Suspect label.

Key issues observed
-------------------
- Noisy snippet selection: extractive summarizer sometimes pulled UI or navigation fragments rather than main body text.
- Weak sentence scoring: TF-IDF-only selection favored surface tokens rather than human-meaningful sentences.
- Repetitive/overbroad rationales: Appendix repeated a generic "Missing open-graph metadata..." rationale for most items even when irrelevant.
- Terms/Privacy messages: one rationale claimed missing Terms/Privacy despite ingestion-level metadata possibly having the links — prefer ingestion metadata when available.

Prioritized, concrete fixes (quick to implement)
------------------------------------------------
1. Prefer article/long-paragraph text: when present, prefer `<article>`, `<main>`, or the longest contiguous text block as the source for extractive candidates.
2. Post-process descriptions to a 2-sentence / ~160-char limit and normalize whitespace and punctuation.
3. Noisy-snippet filter: reject candidate sentences with many short/non-alpha tokens or navigation keywords ("menu", "plan itinerary", etc.).
4. Rationales should be specific: surface ingestion metadata first (e.g., `meta['terms']`/`meta['privacy']`) and only include OG-metadata notes when OG/Twitter meta was actually absent.

Medium-priority improvements
---------------------------
- Combine TF-IDF with position/length heuristics (prefer sentences early in long paragraphs or within `<article>`).
- Add a simple language-coverage/gibberish detector to drop low-information candidates.
- Expose a short provenance tag for each description: "(source: body)" or "(source: og:description)".

Optional / higher-effort
------------------------
- Add an LLM-based rewrite pass for 2-line summaries behind a flag like `--use-llm-descriptions` or reuse existing `--use-llm-examples` flag for gated rewrites.
- Add unit tests for the summarizer and appendix heuristics (fixtures that include noisy UI snippets, long-article content, and missing OG meta).

Next steps recommended
----------------------
1. Implement the quick fixes in `reporting/markdown_generator.py` (prefer article, trim to 2 lines, noisy-snippet filter, rationales from ingestion meta). I can implement the quick fixes and re-run the report now if you want.
2. Add summarizer unit tests and CI checks to prevent regression.
3. After fixes, re-run the pipeline and validate that per-item descriptions are concise, coherent, and aligned with labels.

How to bootstrap a new chat with this project
-------------------------------------------
Use the kickstart blurb already included above and point the assistant at `docs/CHAT_SUMMARY.md` so it loads this appended review automatically.
