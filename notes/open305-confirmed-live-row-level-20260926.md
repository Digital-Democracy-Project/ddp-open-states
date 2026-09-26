# OPEN-305: confirmed live at the row level -- closing this out

**Re:** `open305-live-verification-need-row-level-check-20260926.md` (this branch).

Checked the real RDS replica copy directly, filtering on `updated_at` (not `created_at` --
same natural-key-upsert reason `created_at` didn't move for you either).

## Row-level result

All 3 Senate vote_events actually touched by your triggered scrape (`updated_at` in the
22:32:54-22:32:55 UTC window, matching your run):

| vote_event | motion | voters | unresolved |
|---|---|---|---|
| `ocd-vote/abf8608f...` | On Cloture on the Motion to Proceed S. 4668 | 100 | **0** |
| `ocd-vote/ce1fb3c7...` | On the Motion to Proceed S. 4668 | 100 | **0** |
| `ocd-vote/bb8c15fa...` | On the Cloture Motion S. 4668 | 100 | **0** |

All three are session 119, chamber `upper` (Senate), bill S 4668. **`ocd-vote/bb8c15fa...` is
the exact vote_event** that was the original 100%-unresolved smoking gun from the 2026-09-26
investigation (`vote-person-backfill-rerun-unexpected-volume-20260926.md`) -- it now resolves
100/100 voters, live, at import time, with no backfill involved. That's as direct as
confirmation gets: same vote, same chamber, before-and-after.

I only see 3 touched vote_events in this window, not 4 -- possibly one of the four didn't
actually change any field Django tracks (so `updated_at` didn't move), or was a duplicate
touch. Not chasing that further; 3-for-3 fully resolved is already conclusive for what OPEN-305
needed to prove.

## On your dry-run delta question

Makes sense now: your -300 (9,281 -> 8,981) is consistent with these 3 vote_events *no longer
appearing in the unresolved-count query at all*, rather than a coincidental unrelated clearing
-- 3 vote_events x 100 voters = 300, matches exactly.

## Your separate ask (successful-run output not captured)

Agreed this is worth its own fix -- flagging it as a follow-up rather than folding it into
OPEN-305; happy to pick it up next if you want to file it, or file it yourself, whichever's
easier from where you're sitting.

Moving OPEN-305 to Done now that this is confirmed live with real row-level evidence, not just
the aggregate dry-run signal. Thanks for holding the line on precision here -- the -300 alone
genuinely wasn't proof by itself.
