# Auth failure lead: check whether ddp-sync's own .env is stale, not the credential itself

*Replies to `notes/step3-networking-fixed-now-auth-failure-20260909.md`.* Checked the Django DB
connection code this ties into (`openstates-core`'s `init_django()`,
`openstates/utils/django.py`): it's a plain `dj_database_url.parse(os.environ["DATABASE_URL"])`,
no custom SSL handling, no shell re-interpretation of the string. Nothing there would mangle a
URL that's otherwise correct.

That narrows it: since the same `RDS_DATABASE_URL` value worked for today's RDS backfill dry-runs
(per your own note), and `_launch_archive_fargate_task()` (`ddp-sync`'s
`openstates_archive.py:403`) just does `os.environ.get("RDS_DATABASE_URL")` and passes it through
verbatim as the container's `DATABASE_URL` override -- no transformation on that side either --
the most likely explanation isn't a parsing bug or a rotated-and-not-yet-known password. It's that
**`/opt/ddp-sync/.env`'s `RDS_DATABASE_URL` may simply be a different, stale value** from whatever
the backfill dry-run tool actually read today.

## Ask

Please check, without printing the actual password anywhere:

1. Which `.env` file (or Secrets Manager reference) the backfill dry-run tool sourced its
   `RDS_DATABASE_URL`/`DATABASE_URL` from today, and its last-modified timestamp.
2. `/opt/ddp-sync/.env`'s last-modified timestamp for `RDS_DATABASE_URL` specifically.
3. Whether those two timestamps/sources line up, or whether `ddp-sync`'s copy predates a rotation
   (check `deploy/rotate-database-url.sh`'s run history / last-run timestamp, OPEN-193 precedent)
   that the backfill tool's source already picked up but `ddp-sync`'s `.env` didn't.

If `ddp-sync`'s `.env` is stale, updating it should be enough -- no code or task-def change
needed, same as the SG rules. If the two sources actually match, that rules out staleness and
we'll need to look elsewhere (worth double-checking then whether RDS enforces SSL and the
container's psycopg2/libpq build behaves differently than the host's -- but only if the simpler
staleness explanation is ruled out first).
