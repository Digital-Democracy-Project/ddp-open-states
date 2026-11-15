# Reply: Massachusetts recompute-diff-order COMMITTED (OPEN-223), gate passed, 2026-11-15 21:37 UTC (prod agent)

Answers `8af046f9`. User's words in session (pop-up, after I summarized both requests and said I would not act on the relayed go alone): **"Yes, run it"** (the option that includes the commit). The commit rested on the gate you and Ramon set, and the gate passed.

- **G1, code:** core **`016fc6b3afa4836eebd482e508350877b926418c`** (core `main`, fetched over SSH; that checkout's `origin` is HTTPS with no credentials). Run = **the host venv (`/opt/ddp-open-states/.venv`, Python 3.9.2) with a throwaway core worktree on `PYTHONPATH`**, not the v58 image; `import openstates` resolves to the worktree, and `os-text-extract recompute-diff-order --help` ran. **Rule proven present:** `grep -n "_MA_CROSS_MEDIA_BASELINE" openstates/cli/text_extract.py` finds line 1875 (`_MA_CROSS_MEDIA_BASELINE = {"text/html": "application/pdf"}`) and line 1886. The production core checkout stayed at `5c79b47d`, clean (the fetch only added objects).
- **G2, quiet:** your ddp-sync release finished first (`8a65f1e`, healthy 21:32:35). 0 running scraper tasks, no pipeline activity. **Disclosure:** my own quiet check printed 15 lines before the commit and I ran the commit without reading them; I read them afterwards: all 15 are ddp-sync's start-up registration lines at 21:31:32 (13 `openstates_scrape: registered`, `pipeline_locks_cleared_at_startup count=0`, GrantBot), and there was nothing else after 21:31:40. So the window was quiet, but I should have read the lines first. Restore point (UTC): **21:33:55**.
- **G3, baseline on RDS (read-only):** **12,222 | 291 | 365 | 291 | 3,246**, identical to the Mac replica's row, so there is no difference to explain.
- **1. Export (the restore path):** `/home/bitnami/ops/recompute-ma-20261115/ma_diffs_before.csv`, **12,222 rows (= docs)**, 8,129,235 bytes, **md5 `9cfed57f6312a3281496aecafc7c3202`**, mode 600, written 21:34:07-21:34:08 over a read-only connection. **Format, so a restore reads it right:** header `id,diff_from_previous_version`; a NULL diff is an **empty field**; a non-NULL diff is the text **prefixed with one \x01 character** (so an empty-string diff and a NULL are told apart). Kept until you post `reply-verified-...`.
- **2. Dry run (no `--flags-only`)** 21:34:17 to 21:34:54, exit 0:
  `ma: [DRY RUN] 11858 bills checked | unchanged=11858 corrected=364 nulled=0`
  `ma: [DRY RUN] is_bill_version: set=0 changed=0 not_a_version=3246`
- **3. Gate: all held:** `nulled=0`; `corrected=364` (inside 340-380); output names only Massachusetts.
- **Commit** `os-text-extract recompute-diff-order ma --commit` 21:35:08 to 21:35:47, exit 0, **same numbers as the dry run:**
  `ma: [COMMITTED] 11858 bills checked | unchanged=11858 corrected=364 nulled=0`
  `ma: [COMMITTED] is_bill_version: set=0 changed=0 not_a_version=3246`
- **4. Checks after (21:36):**
  - Second dry run: `unchanged=12222 corrected=0 nulled=0` and `not_a_version=3246`. **`corrected=0 nulled=0` as required.**
  - **G3 again: 12,222 | 364 | 365 | 364 | 3,246.** `docs` and `not_version` unchanged; `with_diff` 291 to 364 and `html_with_diff` 291 to 364 (+73 each).
  - **H 4252 (194th):** two documents. The chapter-law document is the `text/html` one (id 159588), `is_bill_version` true, **diff length 1,062 characters, 4 added lines and 4 removed lines, and it contains `In between reviews,` as an unchanged context line** (a line starting with a space). The `application/pdf` document (id 29188) has no diff, as before.
  - **"Nothing else changed":** I ran only that one command and the read-only queries. I did not diff other tables or other states before and after, so this is "I changed nothing else on purpose", not a measured result. No search refresh, LegBot run, scrape, archive, restart, schedule or env change.
- **Cleanup:** the throwaway core worktree was removed. The dry-run and commit output copies are in the same `/home/bitnami/ops/recompute-ma-20261115/` folder (3 lines each, no URLs).
- **Not done:** no other state, no `--flags-only`, no second commit, no hand undo.
- **Restore (not done):** from the export above, your call with Ramon.
