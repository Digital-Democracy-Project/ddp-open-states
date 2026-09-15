# Correction: "MI retry confirms the text-extraction fix worked" -- no extraction fix exists, this was a timing coincidence

Re: `mi-retry-after-extraction-fix-20260914.md` (35 failures -> 0). Ramon asked me to reconcile
this against my own production findings (`mi-165-failed-extractions-two-distinct-causes-*.md`,
`mi-165-real-legbot-impact-only-17-actually-fail-*.md`). They're not the same bug, and the "35 ->
0" result isn't evidence either one got fixed.

**The 35-failure sample's root cause (per your own earlier note,
`mi-first-real-test-archiving-lag-20260914.md`) was "no archived text exists yet"** -- bills
introduced 5-9 days before the test, MI's archiver (weekly schedule) hadn't reached them. That's
a scheduling/lag gap, not a text-extraction bug. It's a different problem from the 165 I
diagnosed (extraction failing on documents that WERE already archived).

**No text-extraction fix was ever written.** Checked `git log` across ddp-open-states and
openstates-core for anything touching extraction logic since my diagnosis (`e15cfc0`) -- nothing
merged. The two real root causes I found (scraper wrong-page capture for "Substitute" versions;
extraction-tool incompatibility with old XHTML for Senate Enrolled Resolutions) are both still
unfixed code.

**What actually happened, confirmed against real production RDS**: I looked up SB 1148 (the
specific bill your first note cited as a failure example, `first_action_date=2026-09-09`, no
archived text at the time). It now has two archived `BillVersionDocument` rows, `archived_at`
2026-09-14 21:05:33 UTC and 22:35:18 UTC -- both real text, 6987 and 7239 chars. Those two
timestamps line up exactly with the two one-off Michigan archiver Fargate runs I ran that same
day (Ramon's request, to recover WAF-blocked documents from the 165 batch) -- one initial run,
one retry a couple hours later. Your retry test ran afterward (git commit timestamp 23:06:34 UTC)
and simply found the text my manual runs had already produced in the meantime. Same pattern
almost certainly explains the other 34 -- newly-introduced bills swept up incidentally by a
manual archiver run that had nothing to do with their own content-quality path.

**So: the archiving-lag gap is NOT fixed, just masked for this one sample by a one-off manual
run.** The next batch of newly-introduced MI bills will hit the exact same "no archived text
yet" failure the moment nobody happens to run a manual sweep first -- this is the same underlying
issue as the still-open MI-nightly-schedule / archive-after-scrape-sequencing ask from
`legbot-trigger-paused-and-mi-nightly-schedule-request-20260914.md`. Flagging so this doesn't get
marked resolved by mistake -- suggest re-labeling that note's conclusion, or at minimum not
treating "0 failures on this one retest" as confirmation of anything beyond "the bills happened
to have text by the time I checked."

The separate 165-failed-extraction thread (17 genuinely-stuck documents after retry) is
unaffected by any of this and remains open on its own, unrelated fix.
