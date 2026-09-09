# The stale-credential issue isn't just blocking my validation -- tonight's scheduled jobs will hit it too

*Follow-up to `notes/confirmed-stale-credential-not-fargate-plumbing-20260909.md`.* Ramon asked
whether any other scraper tasks have failed from this. Checked before answering, rather than
guessing:

- `aws ecs list-tasks --cluster ddp-scrapers --desired-status STOPPED` only shows my two archive
  validation tasks in the current retention window — no other recent failures visible there.
- `ddp-sync`'s own logs: the last scheduled collect+load triggers (`wa`, `usa`) fired
  ~02:30-03:10 UTC today, well *before* the credential apparently changed (my RDS backfill
  dry-runs, using this same `/opt/ddp-sync/.env` value, succeeded earlier today too). Nothing
  else has attempted an RDS connection since.
- `api-v3`'s logs show zero auth errors — consistent with it holding an already-established
  connection from before the rotation (Postgres doesn't drop existing sessions on a password
  change, only new connection attempts need the current one). Not evidence it's unaffected, just
  that it hasn't needed to reconnect yet.

**So: nothing else has failed yet, but only because nothing else has tried since the rotation.**
The next real scheduled collect+load cycle (`fl`/`wa`/`usa`, ~01:00-03:00 UTC tonight) will hit
the identical `password authentication failed for user "openstates_admin"` wall on its load step,
same as my validation runs — that's roughly 8 hours from now. This raises the priority of the
credential fix above just my OPEN-192 validation thread; it's a real production risk tonight, not
only a blocker for this one investigation.
