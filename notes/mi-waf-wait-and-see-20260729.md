# MI bill-archive WAF block: UA fix didn't help, decided to wait and see (2026-07-29)

## What happened

MI's bill-document archive (`os-text-extract archive mi`) has hit `legislature.mi.gov`'s bot
protection twice now:

- First attempt (2026-07-28 13:00, `logs/mi-full-archive-20260728-blocked-attempt.log`) —
  repeated dropped connections, no clean block signature yet (block-page detection didn't exist
  yet at this point).
- Second attempt (2026-07-28 16:22, `logs/mi-full-archive-20260728.log`) — got through 67 bills /
  201 documents, then tripped the new circuit breaker after 3 consecutive blocked responses
  (`SiteBlockedError`), each one either a `user validation required` block-page marker or a PDF
  request coming back as HTML.

## The UA fix (real, merged, but didn't fix it)

`openstates-core` got three fixes same day, all on `local-patches`/live in production now:

- `5703bb2`/`5f12d0d` — block-page detection + a 3-strikes circuit breaker (`CONSECUTIVE_BLOCK_LIMIT`)
  + a hardcoded per-jurisdiction User-Agent table so MI's archive fetches use the same Firefox UA
  as `scrapers/mi/bills.py`'s own scraper (which has never been blocked).
- `eede4fd`/`1e1d95c` — replaced the hardcoded table with a dynamic import of each jurisdiction's
  own `USER_AGENT` constant, so it can't drift out of sync.

Confirmed live in the production venv: `importlib.import_module("mi.bills").USER_AGENT` resolves
to the exact same Firefox UA the real MI scraper sends.

**This did not fix the block.** The fix landed in the working tree at 15:23 on 7/28; the second
blocked run started an hour later at 16:22, with the fix already active, and still got blocked.
Ramon's own commit message on `5703bb2` says it plainly: "confirmed today that MI's WAF was still
blocking hours later on a completely fresh, cookie-less request." So this isn't a stale-cookie
issue (unlike the earlier FL House WAF fix, see `project-fl-house-waf-fix` in agent memory) and
isn't a UA-mismatch issue either — something else is triggering it, most likely IP- or
rate-reputation-based rather than anything a per-request header can fix.

## Decision: wait and see, don't manually retry MI this week

MI is still enabled in `ARCHIVE_ENABLED_STATES` (not disabled), so nothing needs flipping. The
open question is just *when* to try again. Manually re-running the archive now would send more
requests from the same IP while whatever reputation/rate signal caused the block is presumably
still warm — plausibly counterproductive if it's TTL-based.

**Chosen approach:** don't manually restart MI's archive. Let it sit idle until its next
regularly-scheduled run — the Sunday secondary-group job (`va`, `mi`, `ma`, `ut`, `az` @ 02:00 UTC,
per `ddp-sync/config/sync_schedule.yaml`), next occurrence **2026-08-02 02:00 UTC / 2026-08-01
22:00 EDT**. That's roughly a week of no MI traffic to `legislature.mi.gov` at all (the regular MI
*scraper* — a separate code path, never blocked — will still run its own daily/weekly cadence
independent of this).

**What to check after that run:** whether MI's archive step gets further than 67 bills before
tripping the breaker again. If it does, that's real evidence the block was TTL/reputation-based
and clears with idle time — worth documenting as a MI-specific operational pattern (e.g. "don't
archive-backfill MI more than once a week"). If it blocks again immediately, that rules out simple
time-based reputation decay and the next step is figuring out what's actually fingerprinting us
(TLS/JA3, request pacing/concurrency, something session-level the real scraper does that the
archiver doesn't, etc.) — see the open question raised in the prior conversation about whether the
regular MI scraper takes a meaningfully different path/pacing than the archiver.
