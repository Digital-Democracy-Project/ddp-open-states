# Verified (Mac side): Alabama `recompute-diff-order --flags-only` (OPEN-525). 2026-11-10 about 17:25 UTC

Answers your `74b0318`. **Nothing further is asked of you for this step.**

* **Mac replica applied it:** Alabama now reads `2923 | 0 | 498 | 918` (docs, unmarked, not a version, with comparison), the same as your after row. That means 45 → 498 marked not-a-version, 0 unmarked, comparisons unchanged.
* **Alabama's Stage 3 version-stage gate** (`quality_check.py --structural al`, with DDP openstates-core main on `PYTHONPATH`): **0 of 2,922 versions without a stage (PASS)**, against 453 (15.5%, FAIL) before.
* **Other states:** not compared against a before-snapshot from either side (yours had none either). The command was Alabama-only with `--flags-only`, and my 11-10 classification check of every stored version showed only Alabama's 453 change under the new rule.
* **Still open for Alabama** (not for you now): sponsorship attribution 134 of 1,507 (OPEN-526 merged, waits for a people load and Alabama's next scrape); map outlines (BROKER-464); the manifest change after the pipeline release.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
