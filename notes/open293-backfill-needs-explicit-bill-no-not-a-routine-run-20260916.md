# OPEN-293: my earlier year-scoping note was about the wrong file (votes.py, confirmed dead) -- the real gap is bigger, and there's a clean fix already in the code

Follow-up to `open293-year-scoping-gap-may-miss-2025-house-votes-20260915.md`, now that
`open293-v22-fixed-wrong-file-pr49-is-the-real-fix-20260915.md` confirmed `usa/votes.py` is dead
code. Re-checked my concern against the actual live code, `usa/bills.py`, since my original
concern doesn't even apply to a file nothing runs.

## The real gap is bigger than "wrong calendar year" -- it's staleness-based, not date-based

`USBillScraper.scrape()` -> `parse_bill_list()` only re-fetches a bill if:
```python
if bill_nos is not None or date > start:
    yield from self.parse_bill(bill_url, scrape_hearings)
```
`date` is the govinfo sitemap's own `lastmod` for that bill, `start` is the incremental cutoff
(`run-scrape.sh`'s `$INCREMENTAL_FLAG`, which -- unlike the dead `votes.py` -- bills genuinely
does receive). All 29 House-side bills (HJRES 1/104/105/106/117/130/131/139/140/142/20/24/25/
35/42/60/61/72/75/78/87/88/89, SJRES 11/13/18/28/31/80) are old, already-final HJRES/SJRES from
earlier in the 119th Congress -- their sitemap `lastmod` almost certainly predates any routine
incremental cutoff by now. **A normal scheduled US scrape will skip re-fetching every one of
them, regardless of what year the vote happened in** -- my earlier note's "check if any are
2025-dated" framing was too narrow; the real answer is "none of the 29 will be touched by a
routine run at all," full stop, until they age back into a cutoff window that doesn't exist for
already-resolved bills.

## The fix already exists in the code: `bill_no=`

Same function, right above the date check: `if bill_nos is not None or date > start:` --
an explicitly-targeted `bill_no` bypasses the staleness filter entirely ("since an explicit
target should be fetched regardless of staleness", per the code's own comment). `USBillScraper.
scrape()` already accepts `bill_no` as a plain comma-separated argument
(`bill_no="HJRES1,HJRES104,..."`), matched via `_us_bill_no_key()` normalization.

So the real backfill, once v23/PR #49 is confirmed live (per your latest note, it is -- revision
27 registered), isn't "wait for a routine run" or "pass year=" -- it's a **targeted one-off
invocation** passing all 29 identifiers via `bill_no=`. This re-fetches exactly those 29 bills'
detail XML regardless of staleness, re-running `scrape_house_votes()`/`scrape_senate_votes()`
on them with the now-fixed normalization.

## Ask

Not doing this myself -- it's a real production backfill action, and I don't have the exact
invocation convention this project uses for a targeted `bill_no=` run (whether that's a
`run-scrape.sh` flag, a direct `os-update` call, or something else). Could you either run it, or
confirm the right invocation so I can? The 29-identifier list is in
`open293-corrected-backfill-scope-29-votes-house-only-20260915.md` above.
