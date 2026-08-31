# OPEN-191 (Phase 2) — the real ddp-openstates RDS instance

Documents `ddp-openstates`, created by hand via the AWS console on 2026-08-29 — **not** a
throwaway rehearsal copy. Ramon's standing decision: *"we won't throw it away. it becomes real
infrastructure."* This directory captures its actual configuration as Terraform, in the same
spirit as `infra/fargate-spike`: written after the fact to document a real resource, never
applied against it (this account's credential has no `rds:CreateDBInstance`/`iam:*` access at
all, by design).

## What's real and already working

- **Seeded** from the nightly `pg_dump -Fc` backup (`s3://ddp-openstates-backups/db/openstates_<ts>.dump`)
  via `pg_restore` — real production row counts confirmed (US 37,784 / MA 11,406 / FL 7,685 /
  VA 4,380 / MI 3,924 / WA 3,411 / AZ 2,190 / AL 1,507 / UT 1,021 bills).
- **Verified against a real cloud-collected run**: Florida's full `2026` session (1,897 bills /
  2,728 vote events, collected via OPEN-190's `cloud_collector.py` on a real Fargate task) was
  loaded on top via `cloud_loader.py` — `150 updated, 1,747 noop` bills, `157 new, 31 updated,
  2,540 noop` vote events, zero duplicates (row count unchanged before/after: 7,685 both times).
- **Extended to every jurisdiction (2026-08-29/30), not just Florida.** Virginia, Washington,
  Massachusetts, Arizona, and both USA chamber sessions were each collected via real Fargate
  tasks and loaded the same way — zero duplicates on every one (VA 4,380, WA 3,411, MA 11,406,
  AZ 2,190, USA 37,784, all unchanged before/after). Several were launched in parallel over the
  same rehearsal to prove independent per-jurisdiction collection works concurrently, not just
  one jurisdiction at a time. Full-session runs with no prior watermark took hours (WA ~9h,
  MA ~9.5h) — long, but not stuck.
  - **Found and fixed (VA)**: Virginia's default scraper (`VaBillScraper`) requires a Virginia
    LIS API key. It exists in this repo's `.env` (`VA_API_KEY`) but was never in the Fargate task
    definition's environment, so the first two attempts failed with `ScrapeError: no objects
    returned from VaBillScraper` (exit code 1) — the site was reachable the whole time; the
    scraper just silently produced nothing without the key. Diagnosed by reproducing the exact
    failure locally (`docker run` against the same image) after CloudWatch log read access
    became unavailable partway through this rehearsal (see the gap noted below). Fixed by adding
    `VA_API_KEY` to a new task definition revision — see `infra/fargate-spike/variables.tf`'s
    `va_api_key` variable, which also flags that this should move to Secrets Manager rather than
    stay a plain environment variable.
  - **Found and fixed (USA)**: launching both chamber collections (`session=119 chamber=lower` /
    `chamber=upper`) at the same time correctly produced one success and one `EXIT_DO_NOT_RETRY`
    (90) — OPEN-187's cross-machine `SourceLock` is keyed on the jurisdiction alone, so two
    concurrent collections of the same source correctly refuse to race each other; that part is
    working as designed. But relaunching the failed chamber sequentially afterward exposed a
    real, separate bug: `cloud_collector.py`/`cloud_loader.py`'s `scrape_key` was derived from
    the `session` param alone, so both chambers shared one `usa_119` watermark. The second
    chamber silently hydrated the first's watermark and ran "incremental" against a cutoff for a
    chamber it had never collected, crashing with the same `ScrapeError`. Fixed with a shared
    `derive_scrape_key()` that folds every param into the key — see the fix PR, backward
    compatible with every key already persisted (FL/UT unaffected).
  - **MI: correctly refused, by design, not attempted further.** A real Fargate task for `mi`
    stopped almost immediately with `EXIT_DO_NOT_RETRY` — confirmed via S3 that neither
    Michigan's baseline nor a fresh WAF cookie exist in the memory store, so it refused at the
    first safety gate before any request to `legislature.mi.gov`. Zero site traffic. Exactly the
    behavior OPEN-188's "publish, don't call in" design exists to guarantee. MI isn't usable via
    Fargate again until its baseline is externalized and OPEN-188's cookie publisher is
    re-enabled.
  - **Confirmed the WAF/UA resilience code is identical between the Mac and Fargate paths.**
    `resilience_profiles.py`/`fl_cookies.py` are module-level singletons inside `openstates-core`
    itself, not something either runner reimplements — both `run-scrape.sh` (Mac) and
    `cloud_collector.py` (Fargate) invoke the same `os-update <source> --scrape bills` CLI
    against the same installed `openstates-core` package. Fargate needed Dockerfile fixes
    (`poppler-utils`, `playwright install --with-deps chromium`) to make that *same* code path
    runnable in the container — not a second, parallel implementation of it.
  - **Operational gap found, not yet root-caused**: CloudWatch log read access on
    `/ecs/ddp-scrapers` (`logs:GetLogEvents`/`logs:FilterLogEvents`) started being denied to the
    `ddp-scraper` IAM user partway through this rehearsal, after working earlier in the same
    session. Suspected cause (unconfirmed — this policy is hand-edited in the console, not
    Terraform-managed): `infra/fargate-spike/README.md`'s own bootstrap policy scopes the Logs
    statement to `/aws/ecs/ddp-scrapers*`, but the real log group is `/ecs/ddp-scrapers` (no
    `aws/` prefix) — worth checking if the live console policy carried that same mismatch
    forward. Diagnosing the VA failure above had to fall back to a local `docker run`
    reproduction instead of reading the actual Fargate task's logs.
- **Reachable only through the existing WireGuard EC2 jump box** — not publicly accessible. That
  box's security group is an allowed source on this instance's own security group, and it also
  already hosts production `ddp-sync`/`ddp-api`, so those services get direct in-VPC access with
  no extra networking work once Phase 2's actual cutover happens.

## Two deliberate deviations from the plan this ticket originally wrote

1. **Not a throwaway instance** (see above) — this ticket's own text described rehearsing "into a
   throwaway RDS instance." Superseded by Ramon's explicit decision to build the real target now.
2. **A wrong-database mistake, caught and corrected.** An earlier attempt at this rehearsal used
   `pgdump-readonly.sh` (a different, `/usr/local/ddp-db-proxy/`-scoped wrapper) assuming its name
   meant it dumped the OpenStates production database. It doesn't — verified by checking
   `django_migrations` for app names (`common`, `django_celery_beat`, `slackbot`) that don't
   belong to `openstates-core` at all; it resolves to the dev `ddp-broker` database instead, and
   silently ignores any `-h`/`--host` override passed to it. No production data was lost (the
   dump was read-only against its own wrong source), but the `openstates` database on this
   instance had to be dropped and recreated once the mistake was found. See
   `Production_S3_Wrappers.md`'s new section on this, and use `ddp-prod-s3-openstates-backups` +
   `pg_restore` for the actual OpenStates database, not `pgdump-readonly.sh`.

## Operational gotcha worth knowing before touching this again

RDS's auto-generated Secrets Manager password can contain `:` and `[`, both of which break a
naive `postgresql://user:pass@host` connection string — Python's `urllib.parse.urlparse` fails
with `ValueError: Invalid IPv6 URL`. URL-encode the password
(`urllib.parse.quote(password, safe="")`) before building `DATABASE_URL`/`DATABASE_URL_OVERRIDE`.

## OPEN-191's own 4-item validation checklist, status as of 2026-08-31

OPEN-191 lists four things to check before the broker is pointed at this instance. Status,
checked directly rather than assumed:

1. **api-v3 health** — real, independent api-v3 instances confirmed healthy against this RDS
   instance, on both the Mac and (for INFRA-1) a second EC2 host. **Closed.**
2. **A representative response per routed jurisdiction, compared against the old path** —
   **partially closed.** Compared real bills across three jurisdictions (FL HB 1325, VA SB 192,
   WA SB 6099) between local production Postgres and this RDS instance directly — row counts,
   action counts, version counts, and document/version links are identical on every one checked.
   What's still outstanding: the comparison at the api-v3 *application* layer specifically
   (not just the database) against the second, independent api-v3 instance running on the
   `ddp-broker` EC2 host (INFRA-1) — requested via that repo's `notes/ops-handoff` channel, no
   reply as of this writing. Do not treat this line as fully closed until that response arrives
   and actually matches.
3. **Bill-version ordering intact (OPEN-90/92)** — checked directly against a real multi-version
   bill (VA SB 192): api-v3's own response returns versions in the correct stage-aware order
   ("Introduced" before the later committee substitute), not raw insertion or date order, on
   data that's identical between local Postgres and RDS. **Closed** for the case tested; not
   exhaustively verified across every stage-ordering edge case OPEN-90/92 originally found.
4. **Freshness within the agreed window** — **no agreed window exists yet to check against**,
   so this isn't closeable as written. Observed instead, honestly: the newest bill update per
   jurisdiction in RDS ranges from ~2 days old (Florida) to ~2.5 months old (Washington) as of
   this check — reflecting each jurisdiction's own real legislative activity level (Washington's
   own session was less active in this window), not a bug or a stale pipeline. Setting the
   actual "agreed window" this criterion refers to is a decision for whoever owns that SLA, not
   something to infer from one snapshot.

## Explicitly deferred, not attempted here

Three things remain open and are **not** attempted in this pass, on purpose — each is either a
policy call that belongs to Ramon specifically, or a substantial new infrastructure build with
real production risk, not validation of what already exists:

- **The rollback policy decision** (keep loading to both vs. a stated staleness window) —
  OPEN-191's own text frames this as Ramon's call to make in writing before cutover, not
  something to infer or default on his behalf.
- **A read replica** — genuinely new infrastructure (a second RDS instance, replication set up,
  traffic split between it and the primary), not a check against something already built.
- **Pointing `ddp-broker` at this instance** — the actual cutover, which OPEN-191's own
  acceptance criteria explicitly gate on all four validation items passing and the rollback
  policy being decided first. Neither is true yet.

## What this does NOT do

- Does not create the security group or DB subnet group it references — both pre-created out of
  band, same reasoning as `infra/fargate-spike`'s security group.
- Does not point `api-v3` or any request-time traffic at this instance. No read replica exists
  yet. The rollback policy decision (keep loading to both vs. a stated staleness window) is still
  open — see `PLAN-scraper-execution-migration.md`'s Phase 2 section.
- Does not decide the cutover date. This documents the rehearsal that Phase 2 named as a
  prerequisite before any cutover date is set — the rehearsal itself, not the migration.

## Variables that need real values

See `variables.tf`. `vpc_security_group_ids` and `db_subnet_group_name` come from what was
already created by hand in the console; they're not guessed here any more than
`fargate-spike/variables.tf`'s `security_group_id` was.
