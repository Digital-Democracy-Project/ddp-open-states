# Resolution found: this is a backfill, not a code bug -- here's how to run it against real RDS

**Thread:** VOTEBOT-7 / OPEN-2. Closes out the whole investigation on this branch.

## What we found (short version)

Ran the actual, real `resolve_person()` (from the live `ddp-scrapers:v25` image) directly
against current data -- via `docker exec` into the local Postgres replica at `:5433`, which
per `ddp-infra/README.md` has been a live logical-replication subscriber of the RDS instance
since OPEN-271/272/273 -- for every case this thread investigated (Grassley/Senate,
Bean/Carter/House). **All resolved cleanly, correctly, no ambiguity, right now.** There is no
live bug in `resolve_person()` or in the current Person/PersonIdentifier/Membership data.

The "Unknown" votes are frozen at whatever `resolve_person()` found (or didn't) the one time
each vote was originally scraped and imported. The importer never retries resolution for a vote
event on a later scrape of unchanged content, so a stale miss just sits there forever, even
though the same lookup would succeed today. **Fix: re-run resolution against the already-null
rows.** `backfill-vote-person-resolution.py` (this repo's root) already does exactly this --
it's how OPEN-2's original fix got applied to already-scraped data on 2026-07-29. It's safe to
re-run: only touches `voter_id IS NULL` rows, pure identifier lookup (no name matching), can
only fill in a correct match, never introduce a wrong one.

**Tested locally (dry run, against the replica) just now:** 23,047 unresolved vote records
found, 19,803 would resolve, 3,244 stay genuinely unresolvable (no matching identifier or
still ambiguous). Real RDS numbers will differ -- the local replica isn't necessarily 1:1 with
every vote RDS has.

## How to run it against real RDS

The script (`backfill-vote-person-resolution.py`) takes plain env vars
(`OPENSTATES_DB_HOST`/`PORT`/`NAME`/`USER`/`PASSWORD`), not a `DATABASE_URL`. The image already
has a sanctioned way to get a live RDS credential without hunting for one --
`openstates.utils.rds_credentials.resolve_rds_database_url()`, gated behind `RESOLVE_RDS_LIVE=true`,
literally built (per its own docstring) "for a human running an ad-hoc RDS backfill/dry-run
command." This wrapper fetches it and feeds it straight into the backfill script as env vars,
without ever printing the password anywhere:

```python
# run_backfill_against_rds.py -- place next to backfill-vote-person-resolution.py
import os, subprocess, sys
os.environ["RESOLVE_RDS_LIVE"] = "true"
from openstates.utils.rds_credentials import resolve_rds_database_url
import dj_database_url

url, err = resolve_rds_database_url()
if err:
    raise SystemExit(f"could not resolve RDS credential: {err}")
parsed = dj_database_url.parse(url)

env = os.environ.copy()
env["OPENSTATES_DB_HOST"] = parsed["HOST"]
env["OPENSTATES_DB_PORT"] = str(parsed["PORT"])
env["OPENSTATES_DB_NAME"] = parsed["NAME"]
env["OPENSTATES_DB_USER"] = parsed["USER"]
env["OPENSTATES_DB_PASSWORD"] = parsed["PASSWORD"]

subprocess.run(
    [sys.executable, "backfill-vote-person-resolution.py"] + sys.argv[1:],
    env=env, check=True,
)
```

Run it inside the `ddp-scrapers` image (or wherever `openstates-core`'s venv + `dj_database_url`
are already installed) with `backfill-vote-person-resolution.py` copied alongside it:

```bash
python3 run_backfill_against_rds.py --dry-run
```

**Please run `--dry-run` first and report the counts back on this branch before running for
real.** This writes to production data at real scale (tens of thousands of rows plausible, going
by the local test) -- want a human/Ramon to see the real dry-run numbers before anyone commits
the actual writes, even though the script itself is designed to be additive-only. Once the
dry-run count looks sane, drop `--dry-run` to actually apply it.

Reply on this branch with the dry-run numbers when you get to it.
