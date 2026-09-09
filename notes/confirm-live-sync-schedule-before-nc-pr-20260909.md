# Before I add NC: need the live sync_schedule.yaml's real jurisdiction lists -- git doesn't have them

Separate thread from the RDS credential incident above. Ramon asked to get NC onto `ddp-sync`'s
real recurring cloud-path schedule, following up on the Stage 6 findings (NC has zero recurring
cycles anywhere).

**Found a real gap first, before writing any PR:** `ddp-sync-dev`'s `main` (freshly fetched,
confirmed identical to `origin/main`, no local drift) has
`openstates_scrape.cloud_path.jurisdictions: []` -- genuinely empty. The 8-item list your earlier
note quoted (`["fl","wa","usa","va","mi","ma","ut","az"]`) does not exist anywhere in this
repo's committed file (searched for the literal string, no match). Same question for
`openstates_archive.jurisdictions` -- git has a different/shorter list than the 9-item one
(`["fl","ut","az","wa","va","mi","ma","al","us"]`) your notes cited.

This means the live host's `config/sync_schedule.yaml` has real production jurisdiction values
that were never committed back to git -- a real PR-discipline gap on exactly the file this NC
change needs to touch. If I write a PR off git's current (stale, empty-ish) content and it's ever
deployed by overwriting the live file, it would wipe out the other production jurisdictions, not
just fail to add NC.

## Ask

Please paste back the live host's actual current, full content of:

1. `openstates_scrape.cloud_path.jurisdictions` (and `enabled:`, to confirm it's genuinely
   `true` live even though git says `false`)
2. `openstates_archive.jurisdictions`

And separately: is the live `config/sync_schedule.yaml` ever actually replaced by a fresh git
checkout (e.g. on a redeploy/restart), or is it hand-edited in place on that host and never
re-synced? If it's the latter, that's worth its own ticket (this is the same "merged ≠ running,
and now also committed ≠ running" shape OPEN-247 already exists to fix) -- but tell me what's
real first, I don't want to guess at scope here.

Once I have the real current lists, I'll write one PR that both reconciles git to match live
reality and adds `nc` to both lists -- clearly separated so the reconciliation part is easy to
verify against what you report.
