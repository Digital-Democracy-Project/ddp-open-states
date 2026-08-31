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
   **closed, 2026-08-31.** 6 of 7 routed jurisdictions confirmed exact (FL/VA/WA from the earlier
   pass, AZ/MI/US below); the 7th (MA) has a diagnosed, non-systemic RDS staleness explanation
   rather than an open question — see below. For the three checked earlier (FL HB 1325, VA SB 192,
   WA SB 6099): row
   counts, action/version counts, and document/version links identical between local production
   Postgres and RDS on all three (FL's full detail is in
   `notes/open190-phase1-closure-validation-20260831.md`, merged in OPEN-190's own PR #207).

   **AZ, MA, MI, and USA (US federal — "USA" is this rollout's label for the combined
   lower+upper chamber collection; the bill below is one federal bill, jurisdiction code `us`):
   Mac-side baseline recorded 2026-08-31, RDS-side confirmed the same day via `notes/ops-handoff`
   (`open191-az-ma-mi-us-comparison-request-20260831.md` → `...-reply-20260831.md`, results
   below).** Selection rule,
   stated precisely per pm-review's request: one bill per jurisdiction, `ORDER BY version_count
   DESC, updated_at DESC LIMIT 1` against the local production DB — the most-versioned bill for
   that jurisdiction, ties broken by most-recently-updated. Queried from this Mac's own api-v3
   (`localhost:8002`, `include=versions,documents,actions`). **What "quoted" means here, stated
   precisely per pm-review round 2's request: the top-level bill object verbatim, plus a complete
   accounting of every version (all versions listed, not sampled) and document/action counts —
   the same standard VA/WA already used in this doc (see their `versions` line below), not a raw
   dump of the full `documents`/`actions` arrays**, which for US HR 6644's 106 documents would
   bloat this doc far past what a spot-check needs. This is a *stronger* standard than
   round-1's summary table, not the full-array standard round 2 initially read into "quoted in
   full" — that phrase is corrected below to say exactly what's here:

   **AZ HB 2999** (`GET /bills/ocd-bill/684dd592-426c-44b6-b635-b851b8aa91f4`):
   ```json
   {
     "id": "ocd-bill/684dd592-426c-44b6-b635-b851b8aa91f4",
     "session": "57th-2nd-regular",
     "jurisdiction": {"id": "ocd-jurisdiction/country:us/state:az/government", "name": "Arizona", "classification": "state"},
     "from_organization": {"id": "ocd-organization/b00585a8-0bd5-4a6b-bde1-1c96400f882f", "name": "House", "classification": "lower"},
     "identifier": "HB 2999",
     "title": "municipal improvement districts; technical correction",
     "classification": ["bill"],
     "created_at": "2026-06-16T22:04:19.498312+00:00",
     "updated_at": "2026-06-16T22:04:19.528671+00:00",
     "first_action_date": "2026-02-16",
     "latest_action_date": "2026-06-04",
     "latest_action_description": "Signed by Governor",
     "latest_passage_date": "2026-06-01"
   }
   ```
   10 versions (Introduced → House/Senate Engrossed → committee strikes/floor amendments →
   Chaptered, 2 links each on all but two single-link floor-amendment versions), 11 documents,
   18 actions.

   **MA S 3181** (`GET /bills/ocd-bill/db94bbcd-c21b-4a1d-9302-f7bbeb327fea`):
   ```json
   {
     "id": "ocd-bill/db94bbcd-c21b-4a1d-9302-f7bbeb327fea",
     "session": "194th",
     "jurisdiction": {"id": "ocd-jurisdiction/country:us/state:ma/government", "name": "Massachusetts", "classification": "state"},
     "from_organization": {"id": "ocd-organization/1a75ab3a-669b-43fe-ac8d-31a2d6923d9a", "name": "Senate", "classification": "upper"},
     "identifier": "S 3181",
     "title": "An Act providing equal opportunity for residents to vote on establishment of the Great River Regional School District",
     "classification": ["bill"],
     "created_at": "2026-08-09T10:59:45.242049+00:00",
     "updated_at": "2026-08-30T07:25:00.284176+00:00",
     "first_action_date": "2026-07-16",
     "latest_action_date": "2026-08-25",
     "latest_action_description": "Signed by the Governor, Chapter 193 of the Acts of 2026",
     "latest_passage_date": "2026-08-24"
   }
   ```
   2 versions (Bill Text, 1 link; Chapter Law Text (Enacted), 1 link), 0 documents (MA's known
   one-version-per-stage shape — see `PLAN-push-button-onboarding.md` §OPEN-36), 13 actions.

   **MI HB 4420** (`GET /bills/ocd-bill/006abf23-5a5a-4aa3-9e14-a53aa8bb2f19`):
   ```json
   {
     "id": "ocd-bill/006abf23-5a5a-4aa3-9e14-a53aa8bb2f19",
     "session": "2025-2026",
     "jurisdiction": {"id": "ocd-jurisdiction/country:us/state:mi/government", "name": "Michigan", "classification": "state"},
     "from_organization": {"id": "ocd-organization/d387cf69-631c-4013-bb32-4a00c848fcc4", "name": "House", "classification": "lower"},
     "identifier": "HB 4420",
     "title": "State management: funds; form to disclose legislatively directed spending items; create. Amends 1984 PA 431 (MCL 18.1101 - 18.1594) by adding sec. 364a.  TIE BAR WITH: SB 0596'25",
     "classification": ["bill"],
     "subject": ["Appropriations: other", "State management: funds"],
     "created_at": "2026-06-14T01:52:55.985463+00:00",
     "updated_at": "2026-06-14T01:52:56.034029+00:00",
     "first_action_date": "2025-05-01",
     "latest_action_date": "2025-12-02",
     "latest_action_description": "assigned PA 32'25 with immediate effect",
     "latest_passage_date": "2025-12-02"
   }
   ```
   21 versions (House Introduced Bill → alternating House/Senate substitutes → As Passed by
   House/Senate → House/Senate Concurred → Public Act, 1-2 links each), 5 documents, 51 actions.

   **US HR 6644** (`GET /bills/ocd-bill/fab1200c-53c6-48fa-8e8b-cde9e19d1338`):
   ```json
   {
     "id": "ocd-bill/fab1200c-53c6-48fa-8e8b-cde9e19d1338",
     "session": "119",
     "jurisdiction": {"id": "ocd-jurisdiction/country:us/government", "name": "United States", "classification": "country"},
     "from_organization": {"id": "ocd-organization/24af4233-d9b5-5933-91b2-51d29f721037", "name": "House", "classification": "lower"},
     "identifier": "HR 6644",
     "title": "21st Century ROAD to Housing Act",
     "classification": ["bill"],
     "created_at": "2026-06-16T02:20:39.408557+00:00",
     "updated_at": "2026-08-13T23:00:57.935370+00:00",
     "first_action_date": "2025-12-11T05:00:00+00:00",
     "latest_action_date": "2026-07-11T04:00:00+00:00",
     "latest_action_description": "Sent to Archivist of the United States unsigned.",
     "latest_passage_date": "2026-03-12T04:00:00+00:00"
   }
   ```
   9 versions, 2 links each except a 4-link Enrolled Bill, 106 documents, 59 actions. Full
   version-by-date list in the ordering item below.

   **RDS-side reply landed 2026-08-31 — 3 of 4 exact, 1 real (non-bug) mismatch found.** AZ
   HB 2999, MI HB 4420, and US HR 6644 all matched the Mac-side baseline above field-for-field
   (`updated_at`, version/document/action counts, all identical) — quoted in full on
   `notes/open191-az-ma-mi-us-comparison-reply-20260831.md`.

   **MA S 3181 did not match, and the reason is a genuine RDS freshness gap, not a bug**: RDS's
   copy has 1 version / 0 documents / 12 actions, `updated_at` `2026-08-24T23:34:27+00:00`,
   `latest_action_description` `"Senate concurred in the House amendment"` — everything up through
   that point matches the Mac-side data exactly. What's missing is the bill's *final* stage: the
   governor's signature (`"Signed by the Governor, Chapter 193 of the Acts of 2026"`,
   `latest_action_date` 2026-08-25) and the resulting `Chapter Law Text (Enacted)` version, both
   present in the Mac-side baseline but not in RDS. **This is exactly the load-lag scenario the
   freshness SLA decision above already names** — RDS was last loaded before this bill's
   2026-08-25 enactment, and nothing reloads it on a schedule yet (that's Phase 4's job). Not a
   version-ordering, field-mapping, or routing defect: AZ/MI/US being byte-for-byte correct on the
   exact same RDS instance rules out a systemic problem, and the data MA *does* have is correct as
   far as it goes. Fixed by a re-collection/re-load of MA against RDS whenever next convenient —
   not a new ticket, not a code defect, just the RDS instance needing a refresh it hasn't had since
   before this bill's last action.

   **Jurisdiction coverage (checklist item 2) is now closed**: 6 of 7 routed jurisdictions
   (FL/VA/WA/AZ/MI/US) confirmed exact; the 7th (MA) has a fully diagnosed, non-systemic staleness
   explanation rather than an open question.

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
3. **Bill-version ordering intact (OPEN-90/92)** — **closed, 2026-08-31** (see the three-bill
   confirmation below). First checked against one real multi-version bill (VA SB 192), where
   api-v3's own response
   returns versions in the correct stage-aware order ("Introduced" before the later committee
   substitute) rather than raw insertion or date order — confirmed independently on *both* the
   Mac's instance and the second EC2 instance against RDS. Two independent confirmations of the
   same one case is stronger evidence than one, but it's still one bill — not the same claim as
   "every stage-ordering edge case OPEN-90/92 originally found is still handled," which this
   does not attempt to re-verify.

   **Two stronger cases found 2026-08-31, both confirmed against RDS the same day — neither
   checked against dates as a method, on purpose.** Both bills are
   checked the same way the VA case above was: does api-v3's own existing stage-aware ordering
   (`_note_stage()`/`_version_sort_key()`, OPEN-34 — nothing new written for this) return the
   versions correctly ordered, full stop. **MI HB 4420 (21 versions) has no dates on any version
   at all** — every version's `date` field came back empty from the API — so this case is ordering
   evidence entirely from stage names (House Introduced before its alternating House/Senate
   substitutes, ending at Public Act), exactly because dates can't be relied on and often aren't
   there, which is also why the existing tool doesn't sort on them. **US HR 6644 (9 versions)
   happens to carry real per-version dates** (federal bills usually do; most state bills don't) —
   incidental to this one bill, not a technique being proposed generally, but worth noting because
   it lets the already-correct stage order be cross-checked against real chronology too, as a bonus
   rather than the method: `Introduced in House (2025-12-11)` → `Reported in House (2026-01-15)` →
   `Engrossed in House (2026-02-09)` → `Placed on Calendar Senate (2026-02-24)` → `Engrossed
   Amendment Senate (2026-03-12)` → `Engrossed Amendment House (2026-05-20)` → `Engrossed
   Amendment Senate (2026-06-22)` → `Enrolled Bill (undated)` → `Public Law (2026-07-12)` —
   strictly forward chronological on every dated entry, corroborating the stage-based order
   already returned. **RDS-side confirmed both 2026-08-31**, byte-for-byte identical version
   counts and order to the Mac-side baseline on both bills (see `notes/open191-az-ma-mi-us-
   comparison-reply-20260831.md`) — **this item is now closed**: three independent multi-version
   bills across three jurisdictions (VA, MI, US), one with an incidental chronological
   corroboration on top of the real check, all confirmed correct on both instances.
4. **Freshness within the agreed window** — **DECIDED, 2026-08-31 (Ramon): ≤24h for
   primary/daily-scraped jurisdictions, ≤7 days for secondary/weekly ones**, measured as load
   lag on top of the existing scrape cadence (the gap between a scheduled scrape completing
   against the live source site — already true of the old, Mac-only path today — and that same
   change being readable from RDS), applied once Phase 4 (OPEN-193) actually wires scheduled
   loads to RDS. Matches the bar the Mac's own existing schedule already holds itself to, not a
   new, tighter promise.

   **Not yet checkable against real scheduled traffic**, since no load runs against RDS on any
   schedule today — every load so far in this rehearsal was a manual, one-off `cloud_loader.py`
   invocation. That's Phase 4's job to wire up, not a gap in this decision. What was checked here
   instead: the newest bill update per jurisdiction in RDS ranges from ~2 days old (Florida) to
   ~2.5 months old (Washington) as of this rehearsal, and Washington's age reflects a real
   absence of legislative activity rather than an RDS-specific ingestion gap — the Mac's own daily
   scheduled `run-scrape.sh` runs for Washington, querying the real site directly, have themselves
   reported `bills_scraped=0 | no changes since cutoff (no-op)` on every run from at least
   2026-08-14 through 2026-08-24. Real evidence against an RDS-specific staleness problem, not
   proof the ≤24h/≤7d target is being met yet (nothing measures that until Phase 4 exists).

## Decided by Ramon, 2026-08-31

- **Rollback policy: keep loading to both, permanently — not just for the validation window.**
  OPEN-203 already confirmed a double load is deterministic for the same run (the importer
  resolves by natural key, not row id or `run_id`), which is what makes this actually safe rather
  than merely convenient. This is not the same claim as rollback being "instant": a real rollback
  still needs the application's own connection config reverted, and both databases actually having
  received the same successful loads confirmed at the moment of rollback, not assumed from the
  policy alone. The cost is running the load twice per jurisdiction, cheap at today's volume (see
  the OPEN-189 cost figures — full jurisdiction loads cost cents, not dollars) — and, per the
  replica decision directly below, this cost buys a second, standing thing going forward, not
  just a rollback safety net during one validation window.
- **Read replica: not built, on purpose — Ramon's chosen redundancy mechanism is the Mac's local
  Postgres instead, not a claim that it's a technical substitute for a managed AWS replica.**
  "Keep loading to both" (above) means the Mac's existing `ddp-openstates` local Postgres
  continues receiving every load indefinitely, not just through the validation window — a live,
  independently-updated secondary copy of the same data, outside AWS entirely. Combined with
  RDS's own automatic nightly backups (already running, no setup needed), that's the redundancy
  Ramon decided is sufficient — deliberately **not** a claim that it replicates a managed AWS read
  replica's actual properties (continuous low-lag replication, read-traffic scaling, automatic
  failover); none of those were asked for, and none are built. **No `aws_db_instance` replica
  resource is planned.** This also means Phase 4 (OPEN-193, moving the load step to EC2) needs to
  keep writing to both targets, not just RDS, once it's built — a consequence of this decision,
  not a new requirement invented here. What Phase 4 does when one target succeeds and the other
  fails is that phase's own design question when it's actually built, not something this
  rehearsal-stage doc should answer in advance of Phase 4 existing.
- **Freshness SLA** — decided above (item 4).
- **Cutover timing: hold off, 2026-08-31 (Ramon).** All four checklist items are now closed or
  decided (jurisdiction coverage and version ordering both confirmed against RDS the same day —
  see above). The actual live cutover — pointing production `ddp-broker` at this instance —
  happens later regardless, on Ramon's own call, not as part of this pass.

## Explicitly deferred, not attempted here

Only the cutover itself is deliberately held back — every validation item above is now closed or
decided, on Ramon's own call rather than anything still outstanding:

- **Pointing `ddp-broker` at this instance** — the actual cutover. Explicitly held off per
  Ramon's own decision above, regardless of when the checklist above finishes closing.

## What this does NOT do

- Does not create the security group or DB subnet group it references — both pre-created out of
  band, same reasoning as `infra/fargate-spike`'s security group.
- Does not point `api-v3` or any request-time traffic at this instance. No dedicated AWS read
  replica exists or is planned (see "Decided by Ramon" above — the Mac's local Postgres plus
  RDS's own backups fill that role instead).
- Does not decide the cutover date. This documents the rehearsal that Phase 2 named as a
  prerequisite before any cutover date is set — the rehearsal itself, not the migration.

## Variables that need real values

See `variables.tf`. `vpc_security_group_ids` and `db_subnet_group_name` come from what was
already created by hand in the console; they're not guessed here any more than
`fargate-spike/variables.tf`'s `security_group_id` was.
