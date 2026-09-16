# OPEN-293: updated backfill scope (35 bills / 40 votes) + second bug found and fixed (Senate side)

Update to `ddp-scrapers-v22-what-to-expect-20260915.md` -- that note covered only the
House-side fix (PR #47, already in v22/revision 26). Two things changed since then.

## 1. The real backfill scope is bigger than first estimated, and known precisely now

The original 26-27 bill estimate came from diffing local data against govbot -- but govbot
mirrors the same pre-fix scraper output DDP's own pipeline produced, so it has the identical
blind spot: a bill whose *only* vote was silently dropped shows 0 votes on both sides and
never surfaces as a mismatch. Re-scoped by cross-referencing all 426 tracked HJRES/SJRES
bills (119th Congress) directly against congress.gov's own recorded-vote data instead.

**Real, complete target list: 35 bills, 40 missing votes.**

- **29 House-side** -- PR #47's bug pattern. Ready to re-scrape now; v22/revision 26 is
  registered and will run on the next real scheduled/triggered US job automatically.
- **11 Senate-side, across 8 bills** (`HJRES 105`, `HJRES 25`, `SJRES 34/41/55/80/83/185/196`)
  -- see below, a different bug. Not re-scrapeable yet.

Full list (identifier, missing votes, chamber/roll/date) isn't in this note -- it's the
working target list from scoping, kept on the dev side.

## 2. Second, distinct bug: Senate vote-linking (OPEN-293, PR #48, merged)

Same failure mode as the House bug (a mangled bill_id string matches no real bill, so the
vote silently drops), different root cause, different code path (`scrape_senate_vote`, not
`scrape_house_vote`). The Senate LIS XML gives a bill's type in mixed case with periods
(`"S.J.Res. 55"`); the old normalization was only `.replace(".", "")` -- fixes spacing, not
case (`"SJRes 55"`, not `"SJRES 55"`).

Fixed via `normalize_senate_bill_id()` in `usa/votes.py`, same pattern as PR #47's
`normalize_clerk_bill_id()`. **Merged.** Not yet built into an image -- needs the same
build/push/register process v22 went through (see `RUNBOOK.md`'s "Deploying a Fargate image
change") before the 11 Senate-side votes can be re-scraped. Re-scraping them now, against the
still-unpatched running image, would just fail to link again.

## Status / what's actually done vs. not

- House-side fix: merged, built, deployed (v22/rev 26), **live** -- runs on next US job.
- Senate-side fix: merged, **not yet built/deployed**.
- Backfill execution itself (re-scraping the 29 + 11 votes): **not started** -- scoping is
  done, nothing has been re-scraped/re-imported into production data yet.

No action needed from the prod agent right now beyond awareness -- flagging this so the
Senate-side deploy and the backfill run itself aren't lost track of as separate follow-up
steps.
