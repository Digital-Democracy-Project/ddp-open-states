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
  - **MI: first correctly refused, then genuinely onboarded.** A real Fargate task for `mi`
    stopped almost immediately with `EXIT_DO_NOT_RETRY` on the first attempt — confirmed via S3
    that neither Michigan's baseline nor a fresh WAF cookie existed in the memory store, so it
    refused at the first safety gate before any request to `legislature.mi.gov`. Zero site
    traffic. Exactly the behavior OPEN-188's "publish, don't call in" design exists to guarantee.
    Both prerequisites were then put in place for real: `mi_cookie_publish` was enabled in
    `ddp-sync`'s live schedule (see that repo's own history) and manually triggered once —
    which surfaced and worked around a real, already-known CAMS bug (a dead shared browser with
    no liveness/respawn, `AGENTS-57`, plus a new finding logged there: `OPEN-153`'s isolated-retry
    fallback doesn't reliably obtain Michigan's real WAF cookies even when it reports success) —
    and Michigan's local last-action baseline (`mi_last_actions_2025-2026.json`, 4,013 entries)
    was published to the same memory store. A second real Fargate task then ran a genuine full
    collection under Michigan's 10 req/min cap, explicitly authorized as a real onboarding run
    rather than a verification spot-check.
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
- **Confirmed every completed jurisdiction persisted its incremental watermark**, so tonight's
  rehearsal is genuinely a one-time cold-start cost, not a recurring one: `fl_2026.ts`, `va.ts`,
  `wa.ts`, `az.ts`, `ma.ts`, `usa_119.ts`, and `usa_119_upper.ts` all exist under
  `prod/<source>/_lock`'s sibling paths in the memory store. The next `cloud_collector.py` run
  for any of these will hydrate that watermark, run `mode="incremental"` with a `start=` cutoff,
  and be cheap — matching what the Mac's own scheduled scrapes already do daily. MI's own
  watermark isn't written until its first real cloud run finishes.
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

1. **api-v3 health** — **closed**. "Healthy" here means, on both the Mac's own instance and the
   second, independent one on the `ddp-broker` EC2 host (INFRA-1): `GET /healthz` returns 200,
   *and* a real jurisdiction query (`GET /bills/<id>`) against this RDS instance returns correct,
   current data rather than an error or a stub — not just process-up.
2. **A representative response per routed jurisdiction, compared against the old path** —
   **partially closed; Mac-side evidence now exists for all 7 jurisdictions, RDS-side confirmation
   pending for the last 4.** For the three checked earlier (FL HB 1325, VA SB 192, WA SB 6099): row
   counts, action/version counts, and document/version links identical between local production
   Postgres and RDS on all three (FL's full detail is in
   `notes/open190-phase1-closure-validation-20260831.md`, merged in OPEN-190's own PR #207).

   **AZ, MA, MI, and USA: Mac-side half done 2026-08-31, RDS-side requested via
   `notes/ops-handoff` (`open191-az-ma-mi-us-comparison-request-20260831.md`), not yet replied.**
   One representative bill per jurisdiction, chosen as the most-versioned, most-recently-updated
   bill in each — queried from this Mac's own api-v3 (`localhost:8002`,
   `include=versions,documents,actions`):

   | Jurisdiction | Bill | `updated_at` (Mac) | Versions |
   | --- | --- | --- | --- |
   | AZ | HB 2999 (`ocd-bill/684dd592-426c-44b6-b635-b851b8aa91f4`) | `2026-06-16T22:04:19.528671+00:00` | 10 |
   | MA | S 3181 (`ocd-bill/db94bbcd-c21b-4a1d-9302-f7bbeb327fea`) | `2026-08-30T07:25:00.284176+00:00` | 2 |
   | MI | HB 4420 (`ocd-bill/006abf23-5a5a-4aa3-9e14-a53aa8bb2f19`) | `2026-06-14T01:52:56.034029+00:00` | 21 |
   | US | HR 6644 (`ocd-bill/fab1200c-53c6-48fa-8e8b-cde9e19d1338`) | `2026-08-13T23:00:57.935370+00:00` | 9 |

   Until the RDS-side reply lands, jurisdiction coverage stays **partially** closed — the Mac-side
   half being done isn't the same claim as a confirmed match, and this line will keep saying so
   until the reply is quoted here the same way VA/WA's was.

   The api-v3 *application*-layer comparison against the second EC2 instance is closed for FL
   (quoted in full in #207's own note, field-for-field identical including `updated_at` to the
   microsecond). For VA and WA, the RDS-side response came back via `notes/ops-handoff`
   (`39c9b8a`) — quoting the Mac-side response here directly, matching FL's standard, rather than
   asserting a match without the evidence to back it (a real gap in an earlier version of this
   section, caught via `notes/ops-handoff`):

   **VA SB 192, Mac-side** (`GET /bills/ocd-bill/ae6f0d7a-6a70-430e-a85b-557412caaedf?include=versions`):
   ```json
   {
     "id": "ocd-bill/ae6f0d7a-6a70-430e-a85b-557412caaedf",
     "session": "2027",
     "jurisdiction": {"id": "ocd-jurisdiction/country:us/state:va/government", "name": "Virginia", "classification": "state"},
     "from_organization": {"id": "ocd-organization/9f1a0a17-d2fb-4d0c-90fb-119004411b83", "name": "Senate", "classification": "upper"},
     "identifier": "SB 192",
     "title": "State-owned bottomlands; localities, property interest.",
     "classification": ["bill"],
     "subject": [],
     "extras": {"VA_LEG_ID": 99056},
     "created_at": "2026-08-25T00:31:20.933573+00:00",
     "updated_at": "2026-08-25T00:31:20.943513+00:00",
     "openstates_url": "https://openstates.org/va/bills/2027/SB192/",
     "first_action_date": "2026-01-09",
     "latest_action_date": "2026-07-21",
     "latest_action_description": "Continued from last session",
     "latest_passage_date": ""
   }
   ```
   `versions`: `"Introduced"` (2 links) and `"Agriculture, Conservation and Natural Resources
   Substitute"` (4 links) — same two version notes, same order, as the RDS-side reply.
   Field-for-field identical to the RDS-backed response quoted in
   `notes/open190-191-api-v3-three-bill-comparison-reply-20260831.md`.

   **WA SB 6099, Mac-side** (`GET /bills/ocd-bill/271de7b7-47b6-4992-bb36-40c54862e135`):
   ```json
   {
     "id": "ocd-bill/271de7b7-47b6-4992-bb36-40c54862e135",
     "session": "2025-2026",
     "jurisdiction": {"id": "ocd-jurisdiction/country:us/state:wa/government", "name": "Washington", "classification": "state"},
     "from_organization": {"id": "ocd-organization/ddae63d3-9f3e-4c46-a00f-703fe21b54d1", "name": "Senate", "classification": "upper"},
     "identifier": "SB 6099",
     "title": "Providing basic taxpayer fairness by delaying department of revenue action with regard to tax changes until rule making is finalized.",
     "classification": ["bill"],
     "subject": [],
     "extras": {},
     "created_at": "2026-06-15T23:09:25.014748+00:00",
     "updated_at": "2026-06-15T23:09:25.032880+00:00",
     "openstates_url": "https://openstates.org/wa/bills/2025-2026/SB6099/",
     "first_action_date": "2026-01-13",
     "latest_action_date": "2026-01-13",
     "latest_action_description": "First reading, referred to Ways & Means.",
     "latest_passage_date": ""
   }
   ```
   Identical to the RDS-backed response quoted in the same reply note, field-for-field.

   All three (FL/VA/WA) now genuinely closed at the api-v3 layer, with the actual comparison
   data quoted rather than asserted.
3. **Bill-version ordering intact (OPEN-90/92)** — **partially closed**, not closed outright:
   checked directly against one real multi-version bill (VA SB 192), where api-v3's own response
   returns versions in the correct stage-aware order ("Introduced" before the later committee
   substitute) rather than raw insertion or date order — confirmed independently on *both* the
   Mac's instance and the second EC2 instance against RDS. Two independent confirmations of the
   same one case is stronger evidence than one, but it's still one bill — not the same claim as
   "every stage-ordering edge case OPEN-90/92 originally found is still handled," which this
   does not attempt to re-verify.

   **Two stronger Mac-side cases found 2026-08-31, RDS-side confirmation pending with the same
   request above.** MI HB 4420 (21 versions) correctly orders House Introduced before its
   alternating House/Senate substitutes rather than by insertion order; US HR 6644 (9 versions)
   returns versions in correct forward chronological order by real date (`2025-12-11` Introduced
   through `2026-05-20` Engrossed Amendment House) — the clearest single case yet, since date
   order gives an unambiguous way to check the ordering is actually correct rather than merely
   plausible. Once RDS-side confirms both, this becomes three independent multi-version bills
   across three jurisdictions, one with an explicit date-ordered check, rather than one.
4. **Freshness within the agreed window** — **no agreed window exists yet to check against**,
   so this isn't closeable as written. Observed instead: the newest bill update per jurisdiction
   in RDS ranges from ~2 days old (Florida) to ~2.5 months old (Washington) as of this check.
   Checked whether Washington's age reflects a real absence of legislative activity rather than
   an RDS-specific ingestion gap, rather than assuming it: the Mac's own daily scheduled
   `run-scrape.sh` runs for Washington — the existing, already-trusted path, querying the real
   site directly — have themselves reported `bills_scraped=0 | no changes since cutoff (no-op)`
   on every run from at least 2026-08-14 through 2026-08-24. The same staleness pattern exists on
   the old path too, which is real evidence against an RDS-specific problem, though it does not
   rule out every other possible explanation. Setting the actual "agreed window" this criterion
   refers to is still a decision for whoever owns that SLA, not something this check can settle.

   **Proposal, not a decision (2026-08-31) — offered because a number is more useful to react to
   than a blank.** No load currently runs against RDS on any schedule at all — every load so far
   in this rehearsal was a manual, one-off `cloud_loader.py` invocation, not a recurring job (that
   wiring is Phase 4, OPEN-193, not built yet). So there is nothing to hold to a freshness window
   *yet*, which is different from "no reasonable window exists." The natural candidate is the
   cadence the Mac's own existing schedule already uses and DDP already implicitly promises: **≤24h
   for primary/daily-scraped jurisdictions, ≤7 days for secondary/weekly ones**, applied once
   Phase 4 actually wires scheduled loads to RDS. Proposing this rather than inventing a stricter
   number because it's the bar this migration is supposed to match, not beat — a tighter SLA here
   would be a new, unrequested product commitment, exactly the kind of scope a reviewer should
   catch. **Needs Ramon's explicit sign-off before it's the real answer, not just a plausible one.**

## Decisions needed from Ramon before cutover — proposed, not made

OPEN-191's own text names two of these as explicitly his call, not something to infer or default
on his behalf. Proposals below are offered as a starting point to react to, not a decision already
taken:

- **Rollback policy** (keep loading to both vs. a stated staleness window). OPEN-203 already
  confirmed a double load is deterministic for the same run (the importer resolves by natural key,
  not row id or `run_id`), which is the fact that makes "keep loading to both" actually safe rather
  than merely convenient — that was the one open precondition this option depended on, and it's
  closed. **Proposed: keep loading to both** during the validation window (this rehearsal already
  does, incidentally — the Mac's own local Postgres and RDS have both been loaded independently
  throughout), making rollback genuinely instant rather than a stated-staleness compromise. The
  cost is running the load twice per jurisdiction until Phase 4 consolidates it, which is cheap at
  today's volume (see the OPEN-189 cost figures — full jurisdiction loads cost cents, not dollars).
- **Freshness SLA** — see the proposal directly above.

## Explicitly deferred, not attempted here

One thing remains open and is **not** attempted in this pass, on purpose — substantial new
infrastructure with real production risk, not validation of what already exists, and premature
before the decisions above are actually made:

- **Pointing `ddp-broker` at this instance** — the actual cutover, which OPEN-191's own
  acceptance criteria explicitly gate on all four validation items passing and the rollback
  policy being decided first. Neither is true yet.

## Read replica — deferred deliberately, not forgotten

**Not built, and recommending against building it yet — this is a guard against over-engineering,
not a gap.** OPEN-191's own acceptance criteria name a replica/primary split for site reads versus
load writes, but nothing reads from this instance at request time today (see "What this does NOT
do" below) — `ddp-broker` isn't pointed at it, so there is no live read traffic for a replica to
take on yet. Building one now would be infrastructure with no consumer, sized against a traffic
pattern (`ddp-next` reads via the broker) that doesn't hit this instance at all until cutover.
**Recommended trigger: build it as part of the cutover work itself, sized from real read volume
observed on the *old* path in the weeks immediately before cutover, not estimated now.** This
account's credentials can't create it regardless (`rds:CreateDBInstance` denied, same as the
primary instance) — it needs Ramon's own console access whenever it's actually time.

For when it is wanted, the shape is a one-line addition to what's already documented here:
```hcl
# infra/rds/rds.tf — proposed addition, NOT applied, NOT built
resource "aws_db_instance" "openstates_replica" {
  identifier          = "ddp-openstates-replica"
  replicate_source_db = aws_db_instance.openstates.identifier
  instance_class      = aws_db_instance.openstates.instance_class  # match primary; resize from real read load once observed
  publicly_accessible = false
}
```
Deliberately not more than this: no separate parameter group, no auto-scaling, no cross-AZ decision
made in advance — those are real questions worth answering when there's real read traffic to size
against, not guesses to bake in now.

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
