# UPDATE (not a GO) to `21d55d4` (v81): it also carries **OPEN-777**, the US vote-person backfill marking the bills it fills as updated. ddp-open-states main is now `da043df6`. 2026-11-23 (Mac side, State Specific Handling)

**Not a GO.** Everything in `21d55d4` stands: scrapers `414311c6` or later, core `42b48982`. The Utah re-import (`d7ce0d8`) is unchanged.

## The change added
* **OPEN-777, ddp-open-states #468,** merged by the PM session as `da043df6` (full sha `da043df63371bf17f460d8ab43691ed7c1a39009`).
  * `relink-blank-voters.py` and `backfill-vote-person-resolution.py` now set `opencivicdata_bill.updated_at = clock_timestamp()` for the bills of the votes they fill.
  * They do it on commit only, in the same transaction, and print the count.
  * **Why:** from 2027-01-01 the broker's nightly chain stops, and its after-scrape fetch reads only bills whose timestamp moved.
* **Only the US backfill rides the image.** `deploy-scrapers-image.sh` clones ddp-open-states `main` at build, and the Dockerfile copies `backfill-vote-person-resolution.py` in. So v81 built now carries it with no extra step. `relink-blank-voters.py` runs from a checkout and needs no image.
* No migration and no new setting.

## For the open OPEN-611 commits (your `c5187ea`)
* **No change needed.** The US backfill commit you will run after the ddp-sync rebuild uses whichever image is live then, with or without this change. Until 2027-01-01, the nightly chain reads its 15 fills either way.
* **If v81 is live by then,** its log says how many bills it marked updated; please report that number too.

## After the build
The Mac side checks that the image holds the new `backfill-vote-person-resolution.py`: it contains `clock_timestamp()`.

Tickets: OPEN-777, OPEN-611. Epic OPEN-536.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
