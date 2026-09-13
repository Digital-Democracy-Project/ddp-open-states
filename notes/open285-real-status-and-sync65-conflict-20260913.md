# OPEN-285: real status on all 3 items (not resolved), plus a real conflict found in SYNC-65

## The 3 items, checked directly, honestly

1. **`openstates_people_refresh` clean run: NOT done.** PR #146 (`DATABASE_URL_OVERRIDE` fix) is
   merged to `main` but was **never pulled/deployed on this EC2 host** -- confirmed via
   `git merge-base`, this host's `ddp-sync` checkout is still on PR #145's commit (`d35bf80`),
   several behind. The "seventh attempt" never actually happened. Ramon's impression that this
   was resolved wasn't correct as of this check -- my own fault for not following through and
   confirming after the fix was merged; sorry for the gap.

2. **Legacy crontab entry: gone, but not by me.** `crontab -l` now shows only the map-freshness
   cron job -- `refresh-openstates-people.sh`'s entry (and, separately, the unrelated
   Let's-Encrypt cert-renewal entry) are both absent. I did not remove either, and don't know
   who did or when -- flagging this as a real, unexplained state change rather than claiming
   credit for a "clean run confirmed" removal I never actually did. Worth checking with Ramon
   directly on whether he removed it himself.

3. **IAM EventBridge/Scheduler visibility: still blocked.** Re-confirmed just now, fresh:
   `events:ListRules` still returns `AccessDeniedException` on this host's role. No change.

## Real conflict found in SYNC-65 (#147) -- please don't deploy as-is without addressing this

Found this while checking on item 1 -- `ddp-sync` has a new merged commit, SYNC-65, replacing
the scrape-completion LegBot hook with an archive-completion one. This is the right fix for the
sequencing bug I flagged yesterday (`notes/open280-done-sync59-gap-found-us-backfill-status-
20260913.md`) -- but its own design explicitly assumes archiving only ever runs on the Mac:

> "OPENSTATES_ARCHIVE_ENABLED is only ever true on the Mac's own ddp-sync instance today"

**That's no longer true.** Ramon had me flip `OPENSTATES_ARCHIVE_ENABLED=true` on this EC2 host
too yesterday (OPEN-192), and the `us` archive job already completed here for real via
Fargate. `_maybe_trigger_legbot_for_archive` calls `trigger_scraper_session_pipeline`
**in-process**, on the assumption that archiving-completion always happens on the Mac (where
CAMS/LegBot's own dispatch lives). Confirmed directly: `CAMS_BASE_URL` defaults to
`http://localhost:8000` and is unset on this EC2 host -- no CAMS server exists here.

**Concrete consequence if deployed as-is**: an archive job that completes via THIS EC2 host's
own `ddp-sync` process (any Fargate-run archive this host schedules, like today's `us` run)
would have its hook fire here, try to reach a nonexistent local CAMS endpoint, and silently
fail to ever trigger LegBot -- the sequencing bug gets fixed for Mac-orchestrated archiving,
but a new, symmetric gap opens for EC2-orchestrated archiving. Not deploying this yet pending
your call on how to resolve it -- options that occurred to me, not prescribing one: gate which
host's process actually calls the hook based on which one is "Mac-capable" (env-flag check
before dispatching, same shape as `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED`'s own
per-instance-config posture); or reintroduce a WireGuard hop (mirroring the now-removed
SYNC-59 plumbing, which I've already wired up and verified working -- `MAC_DDP_SYNC_BASE_URL`/
`MAC_DDP_SYNC_API_KEY`, still in place, unused) specifically for the case where the archive
hook fires on a non-Mac host.

Also: `api-v3` PR #11 (the `document_updated_since` filter SYNC-65 needs) is merged upstream
but not deployed on this host's api-v3 instance either -- would need a rebuild+redeploy there
too before SYNC-65 could work at all, separate from the conflict above.

**Still holding `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED=false`** -- now for two reasons: the
original sequencing concern, and this new archive-orchestration conflict in the fix meant to
address it.
