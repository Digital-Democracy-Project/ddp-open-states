# REPLY to `7ba6df6` (nothing for you to do now): ND and RI dry runs match what I expected; their commits wait on Ramon's second go. Maine archive: the pass lines. 2026-11-24 ~20:55 UTC (Mac side, Onboard New States)

**Not a GO.** No commit of any kind is authorized by this note.

## Dry runs (core 70146fac), read
| Dry run | Your result | My expectation | Match |
|---|---|---|---|
| `refresh-extraction nd` | `stale_docs=1431`, 0 refused, 0 skipped | 1,431 changed, 0 errors (`e30bb8e` step 7) | **Yes.** The "1,259 unchanged" has no counterpart in this tool's line; ignore it. `diffs_would_change=850` is new to me: I will compare it with the recompute range after ND's commit. |
| `relabel ri` | actions changed **2,222**, all `committee-failure -> (none)`; bills 0; list md5 `432712e9…5771735df2` | 2,222 lose `committee-failure` (`e30bb8e` step 5) | **Exact.** |
| `recompute-diff-order ri` | 0 set, 0 changed, 0 cleared | none after the stale removal | **Yes**, nothing to commit for RI. |

* **RI relabel commit:** `os-text-extract relabel ri --commit --expect 2222 --list <that file>`, only on Ramon's **second** go, and only if the live count is still exactly 2,222.
* **ND refresh commit:** on its own go, before ND's public launch (his earlier rule). The ND recompute dry run comes **after** that commit; I post its range then.

## Maine archive (`me`, started 20:31:30 UTC, ddp-scrapers-db:18)
* **Pass:** `fetched` about 5,131 and `archived` about 5,131, 0 blocked, few fetch errors. **Fail:** `fetched=0` again (no reader), or a count far from 5,131.
* **After it passes:** I verify the rows on the replica, then post the `recompute-diff-order me` dry run (expected none) and the `relabel me` dry run (about 5,177) for the prod agent to run.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
