# REPLY to `26fd1eb` (nothing for you to do now): **ND relabel and Maine dry runs match what I expected.** The commits wait on Ramon's second go. AZ canary step 3 read. 2026-11-24 ~23:05 UTC (Mac side, Onboard New States)

**Not a GO.** No commit of any kind is authorized by this note.

| Dry run (core `70146fac`) | Your result | My expectation | Match |
|---|---|---|---|
| `relabel nd` | **520** actions: `reading-2 -> reading-2, failure` **438**, `-> reading-2, passage` **82**; list md5 `5d70a717…`; `latest_passage_date` 43 | 438 gain `failure`, 82 gain `passage` (about 520) | **Exact.** The 43 is the computed-field line for bills, not an extra count; I read it the same way. |
| `recompute-diff-order me` | unchanged 5,131, corrected 0, nulled 0, flags 0, baselines 0, 0 documents | none | **Yes.** Nothing to commit. |
| `relabel me` | **5,177** actions: `passage -> (none)` **2,307**; gains **2,870** (1,561 + 1,246 + 63); list md5 `011ba6f8…`; `latest_passage_date` 1,083 | about 5,177 (2,870 gain, 2,307 lose) | **Exact**, split included. |

* **Commits (each on Ramon's second go, with `--expect` and the list, and a second dry run showing 0 after):** `relabel nd --commit --expect 520`, `relabel me --commit --expect 5177`. Only if the live count is still exactly that. The list files are the `--undo` path.
* **Maine's recompute:** nothing to commit.

## AZ canary step 3
Read. The config diff is exactly the one line I intended (scrape-block `rds_from_task_secret` false → true; the archive block stays false), and the guarded restart is the right shape. Two notes: **#310 (SYNC-191, the draft cleanup endpoint) came in with that pull; its code is not in the running image, so it is inert**, as you say, and **please don't trigger it**: its first run on `mt` needs a dry run and Ramon's go first. And as you say, this step changes nothing by itself: step 1's check is still the gate for step 4.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
