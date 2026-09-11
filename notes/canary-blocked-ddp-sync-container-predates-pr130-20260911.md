# Canary trigger returns 404 — this host's ddp-sync container predates PR #130

Tried the supervised dry-run canary. Two real issues found by direct invocation, not
guessed:

1. **Wrong port/path in the note's example command.** The running `ddp-sync-ddp-sync-1`
   container maps `8001`, not `8000`, and every route is prefixed `/ddp-sync/v1/` (confirmed
   via `GET /openapi.json`). Corrected the request to
   `http://localhost:8001/ddp-sync/v1/trigger/openstates-backfill/mi?subcommand=recompute-diff-order&mode=dry-run`.

2. **The endpoint doesn't exist in what's actually running.** Even with the corrected
   path, the container returns `{"detail":"Not Found"}`. Checked `/openapi.json`'s full path
   list directly — no `openstates-backfill` route at all, only `openstates-archive/{target}`
   and `openstates-scrape/{target}`. Confirmed why: the running container
   (`docker inspect` → image `ddp-sync:prod`, created `2026-09-09T19:25:30Z`) predates PR
   #130's merge commit `8f3930f` (`git show -s --format='%ci' 8f3930f` →
   `2026-09-10 21:41:18 -0400`, i.e. last night, after this container was last built). The
   code that adds this trigger genuinely isn't in the deployed image yet.

**Not rebuilding/redeploying `ddp-sync` myself** — it's a broader production service (serves
`legbot`/`votebot`/`webflow`/bill-sync triggers too, not just scraper/archiver work) outside
the scope I've been operating under this session, and I don't have established familiarity
with its deploy process the way I now do for `ddp-scrapers`. Flagging for you or the dev
agent to redeploy `ddp-sync` from current `main` before this canary can run.

Once that's done, I'll re-run the (corrected) trigger command and report the result.
