# Three things: OPEN-280 done, a real SYNC-59 sequencing bug found (please hold), and us backfill status

## OPEN-280: `profiles_profile` dropped from the publication -- done

With Ramon's explicit go-ahead: `ALTER PUBLICATION ddp_legbot_publication DROP TABLE
public.profiles_profile;` -- succeeded. Publication now has 47 tables (was 48). Your side:
refresh the subscription whenever ready; the Mac's existing `profiles_profile` row is
untouched either way, this only stops *future* sync of that table.

## SYNC-59: real sequencing bug found before enabling -- please hold on flipping the flag

Ramon asked a sharp question that led to a real finding: does the LegBot trigger fire after
the *scraper* or the *archiver* completes? Traced it precisely -- **after the scraper (scrape +
RDS-load), not the archiver.** These are two completely separate, independently-scheduled
pipelines with zero connection to each other.

**Why that's a real problem, not just a design choice**: LegBot needs `raw_text` --
`_resolve_bill_source()` (`bill_artifact_generation.py`) only ever reads already-archived,
already-extracted text (`get_archived_bill_text`, OPEN-13) and explicitly has no live-fetch
fallback. If a bill's scrape completes before its text has been archived+extracted (a real,
likely-common ordering given archiving runs on its own separate weekly schedule per
jurisdiction), `_resolve_bill_source()` returns `None`, and `generate_and_store_bill_artifact`
records a row with `status="failed", failure_reason="no_archived_bill_text"` rather than
skipping gracefully.

**The part that makes this a real gap, not a self-healing one**: `session_pipeline_runner.py`'s
own coverage check treats `failed` as terminal -- it's only re-dispatched when the caller
passes `retry_failed=True` (SYNC-42). `trigger_scraper_session_pipeline`
(`scraper_triggered_legbot.py`), the exact function SYNC-59's trigger calls into on the Mac,
defaults `retry_failed=False`. So once a bill gets this specific failure, **nothing brings it
back** -- not the archiver finishing later (no connection to this trigger at all), not a future
scrape of the same session either (unless someone happens to pass `retry_failed=True`, which
the automated path never does by design -- SYNC-42's own doc explicitly frames `retry_failed`
defaulting off for scheduled/automated callers as intentional, "a cron job must keep doing
exactly what it did yesterday").

**Holding on flipping `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED` until this is addressed.** All
the plumbing (URL + matching key, both sides) is otherwise ready to go the moment this is
resolved. Options that occurred to me, not prescribing one: gate the trigger on archiving
having actually run for the touched session first; have the archiver (not just the scraper)
also call this same trigger once it finishes; or pass `retry_failed=True` specifically from
this automated path, accepting the cost of re-checking already-failed rows every time (SYNC-42's
own docstring's stated reason for defaulting it off assumes a *human-reviewed* dispatch cadence,
which doesn't describe this automated trigger's real usage pattern) -- your call, just wanted
the real mechanics on record before anyone assumes flipping this flag is otherwise safe.

## `us refresh-extraction --commit` status, for your records

Succeeded cleanly earlier today (2026-09-13, run `us-refresh-extraction-commit-300e99728ee3`):
`us: [COMMITTED] bills_with_stale_docs=16560 stale_docs=20343 diffs_corrected=3118
docs_skipped=0 docs_refused=0`, ~3h38m, no repeat of the earlier dropped-connection crash. This
closes out all 6 jurisdictions (mi/ut/fl/va/wa/us) in the RDS data-quality backfill -- already
reported in detail on this branch (`notes/us-backfill-commit-succeeded-20260912.md`), flagging
again here since it came up in conversation and I want to make sure it's on your radar too.
