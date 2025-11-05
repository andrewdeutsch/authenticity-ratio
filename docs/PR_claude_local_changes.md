PR: Local branch packaging in-progress reporting and pipeline fixes

Summary
-------
This local PR branch packages in-progress changes made while resolving merge conflicts and improving report generation. The branch includes the following changes:

- reporting/markdown_generator.py
  - Resolved merge conflicts and added robust fallbacks for appendix items.
  - Coerces object-like items to dict-like mappings for stable `.get()` access.
  - Adds optional LLM summarization hooks and a consistent provenance label for generated text.
  - Fixed indentation and syntax issues so module imports cleanly.

- reporting/pdf_generator.py
  - Adds `_coerce_item_to_dict` helper and coerces items before rendering examples/tables.
  - Reuses LLM helper functions when available.

- scripts/run_pipeline.py
  - Minor operational edits and smoke-test run wiring.

Notes
-----
- This branch was created locally to avoid further rebase conflicts while consolidating changes.
- The branch has not been pushed upstream; please review locally and decide whether to push as a feature branch or continue rebasing onto the remote branch.
- LLM client (`scoring/llm_client.py`) remains a placeholder; production usage requires wiring credentials (e.g., `OPENAI_API_KEY`).

How to review locally
---------------------
1. Checkout the branch:

   git checkout pr/claude-local-changes

2. Inspect changes:

   git show --name-only HEAD
   git diff origin/claude/review-recent-issues-011CUYGsbZLemibaVWJiMpuu..pr/claude-local-changes

3. Run smoke test (optional):

   python3 scripts/run_pipeline.py --brand-id test-brand --keywords test --sources brave --max-items 5 --brave-pages 5 --output-dir tmp_smoke --log-level INFO

Next steps
----------
- Optionally push the branch and open a PR on GitHub:

  git push -u origin pr/claude-local-changes

- Or continue resolving remaining rebase conflicts interactively if you prefer rebasing instead of merging.