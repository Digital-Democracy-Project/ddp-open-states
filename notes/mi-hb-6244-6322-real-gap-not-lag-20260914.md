# MI: 87 real Tier 1 bills missing after the govbot zero-padding fix -- HB range is a hole, not lag

Follow-up to the OPEN-289 identifier-normalization fix (PR #254): after fixing govbot's
zero-padding false positive, MI's real Tier 1 gap dropped from a false `missing=1590` to a
real `missing=87`. Traced all 87 directly against the RDS replica (`openstates_rds_repl_20260911`).

**HR (9) and HCR (1) are ordinary lag** -- local's max resolution number is a few behind
govbot's (`HR` local max 341 vs govbot 350, `HCR` local max 8 vs govbot 9), no gaps in
between. Nothing to investigate there.

**HB (77) is a real hole, not lag.** Local's `HB` coverage is clean up through `HB 6243`,
then missing almost the entire `6244`-`6322` range (77 of 79 numbers), then clean again from
`6323` through `6326` (local's actual max -- same as govbot's). Local isn't behind; it has
bills *newer* than the gap.

The two survivors inside the hole (`HB 6287`, `HB 6302`) are the key clue: their local
`created_at` timestamps, and those of the bills right after the hole (`HB 6323`-`6326`), all
fall in the same one-second window -- **2026-09-03 01:05:30-01:05:32 UTC** -- clearly one
scrape run. That run picked up scattered bills from inside the missing range and everything
past it, but skipped the other 75. That's consistent with a partial failure on that specific
run (e.g. a paginated bill-index page for that number range not loading), not a jurisdiction
that's behind on scraping.

**Can't go further from the Mac.** The Mac's local scraper logs don't cover that window --
rotated logs stop 2026-09-02, and the current `scraper.log` only shows archiver activity for
MI around that period, not the metadata scrape itself. Given the ongoing scraper-execution
migration, that 9/3 run may have happened on EC2 rather than the Mac.

**Ask**: can you check EC2-side scrape logs for MI around 2026-09-03 01:05 UTC and see what
happened on that specific run -- a WAF block, a pagination failure, a partial timeout, etc.?
That would confirm (or rule out) a real MI scraper bug worth fixing, versus something
already self-healing on the next full walk.
