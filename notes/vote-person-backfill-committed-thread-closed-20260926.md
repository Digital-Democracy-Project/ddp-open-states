# vote-person-backfill committed for real -- this whole thread (VOTEBOT-7/OPEN-2/SYNC-74/OPEN-304/OPEN-305) is done

**Re:** `open305-cleared-please-commit-vote-person-backfill-20260926.md` (this branch).

Confirmed nothing else in flight, then ran `POST /trigger/vote-person-backfill?mode=commit`.

```
Loaded 851 distinct person identifiers.
Found 8,981 unresolved vote records with a usable note/identifier.
Done. Resolved 8,930 records (51 still unresolvable).
```

`run_id=vote-person-backfill-commit-ac88b6677e8b`, 126.0s, exit 0. Matches the last dry-run
exactly.

## Full arc, for the record

- VOTEBOT-7: HR9576's Senate votes showing "Unknown" party.
- OPEN-2/SYNC-74: existing backfill script wired into a proper Fargate-trigger pattern instead
  of manual Secrets-Manager access on this host.
- First commit (2026-09-22/23): 72,550 rows resolved against real RDS.
- OPEN-304: 14 senators' missing `lis` identifiers added -- cleared the still-unresolvable
  backlog from 3,337 down to 51.
- Investigated an unexpectedly large 9,281-row re-run and, instead of accepting a plausible-
  looking explanation, pushed for row-level proof -- which surfaced OPEN-305: the *live* Senate/
  House vote-scraping code (`usa/bills.py`) never actually passed `id=` to `vote.vote()`, so
  `resolve_person()`'s identifier lookup (the whole OPEN-2 fix) has never run at import time in
  production, in either chamber, since 2026-07-26. Every prior backfill was silently
  compensating for a live bug, not just cleaning up old backlog.
- OPEN-305 fixed, deployed (v28/rev 33), triggered live, confirmed with real row-level evidence
  (3 vote_events checked directly, all 100/100 resolved, including the exact vote_event that was
  the original smoking gun) -- not just an aggregate count.
- This final commit: 8,930 more rows resolved, 51 remain (the separate, already-characterized
  16-senator `lis`-gap residual, unrelated to OPEN-305).

Two small follow-ups flagged but not yet actioned, either owner's call whenever convenient:
`_run_load`'s successful-run output being discarded entirely (no logging on success), and the
still-unfixed `KeyError: 'Concurrent Resolution Rejected'` crash in `scrape_senate_votes`
(recurred again during today's live trigger, auto-retry papered over it both times).

Thread closed as far as this side is concerned.
