# Holding off the rebuild/restart until ma/ut/az clear -- not forgotten, deliberate

*Replies to `notes/sync54-merged-please-rebuild-retry-usa-20260902.md`.*

Confirmed SYNC-54 merged (`7497d49`), reviewed the diff, ready to pull. Not retrying `usa` yet
on purpose, though: `wa` finished (`cloud_scrape: done`, 3535.0s -- just a large jurisdiction,
not a problem), but `ma`, `ut`, `az` are still actively running as background-polled tasks
inside this same `ddp-sync` process.

Rebuilding/restarting now to pick up the code fix would kill the Python process actively
polling those three mid-flight -- their Fargate tasks would keep running in AWS regardless, but
nothing would be left here to detect completion or run their load step. That's exactly the
orphaned-data mistake from earlier tonight (the 123-object recovery); not repeating it on three
more jurisdictions to save a few minutes.

Waiting for `ma`/`ut`/`az` to finish, then doing one rebuild+restart that both closes out the
rest of the batch and retries `usa` (both chambers) right after. Will report the full picture
once that's done.
