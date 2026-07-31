# Plan: Incremental Bill Scraping — All Active Jurisdictions

**Status: REOPENED 2026-07-27, again 2026-07-28, and again 2026-07-30 — core implementation is
live, but not complete, and two separate parts of the surrounding pipeline were actively
destroying data.** All 8 jurisdictions were patched 2026-06-22 and the shell timestamp layer
(`logs/last-run/`) has run nightly since; see `RUNBOOK.md` for operational details. But three of
this plan's own follow-ups were never closed out, and re-investigating why a routine WA scrape was
taking ~70 minutes during an out-of-session week surfaced that this is systemic to three
jurisdictions, not a fluke — see **"Reopened 2026-07-27: the per-bill network floor"** below. Then,
a day later, investigating why Utah had zero archived bill documents found something worse than a
missed efficiency case: **UT's and VA's `start=` implementations were silently deleting each
unchanged bill's already-scraped versions, sponsorships, actions, and votes on every incremental
run** — see **"Reopened 2026-07-28: the UT/VA skip pattern was deleting data, not just saving
time"** below. Both are now fixed (`openstates-scrapers` PRs #10 and #11), but the already-lost
data for both jurisdictions still needs a fresh full scrape to come back. Then, two days after
that, a manually-restarted FL/MA backfill made clear that **"incremental scraping" was never about
when data reaches Postgres at all** — the scrape→import handoff is still one all-or-nothing batch
at the very end of a run, and a run that dies before that point loses everything, including
already-scraped JSON on disk if it's ever retried — see **"Reopened 2026-07-30: import only
happens once, at the very end — a killed scrape loses everything"** below.

**2026-07-30: the import-as-you-go fix (round 3 of the design, below) is approved for
implementation** — landing now in `fix/import-as-you-go-sweep`, in `run-scrape.sh` only. The open
questions listed at the end of that section (partial-run visibility sign-off, sweep
interval/timeout tuning, DB load under FL/USA) are explicitly not blocking implementation — they
gate the *rollout* (opt-in flag, canary jurisdiction first), not writing the code.

## Context

Every nightly scrape was a full rescrape. FL 2026 regular paginates ~2,000 bills
through flsenate.gov and hits flhouse.gov once per bill — 30–40 hours per run due
to bot-detection backoffs. USA federal takes 3–4 hours for 10k+ bills. Both run daily.
WA and the secondary states (MI, UT, MA, AZ, VA) also rescrape fully on their cadences.

Goal: for every jurisdiction, nightly runs only fetch bills updated since the last run.
Implementation is local patches only (no upstream PRs).

---

## Standard pattern (applies to every state)

1. **Shell layer** (`run-scrape.sh`): record a UTC timestamp after each successful import
   in `logs/last-run/<key>.ts`. On the next run, read it back and pass `start=<timestamp>`
   to `os-update`.

2. **Scraper** (`scrapers/<state>/bills.py`): accept a `start=` kwarg in `scrape()`, parse
   it, and skip bills whose last-action/last-modified date is ≤ start. The correct skip
   mechanism in spatula is `raise SkipItem(...)` from `process_item()`.

   **Skip before or instead of yielding, never yield a partially-populated `Bill` — found the
   hard way 2026-07-28 (see "Reopened 2026-07-28" below).** When `Bill()` doesn't exist yet at
   the point of the skip check, don't create it at all (`SkipItem`/`continue` in the list-
   building step, or `return` before construction in a per-bill function). If a `Bill` already
   exists and has been partially populated, skip it by not yielding it at all (plain `continue`,
   or a captured `yield from` return value the caller checks) — never yield it anyway with some
   fields populated and others not. `openstates-core`'s importer deletes a bill's existing
   related items (versions, sponsorships, actions, etc.) whenever a new scrape reports zero of
   them, so a partially-populated yield silently deletes real data on every subsequent
   incremental run against an unchanged bill.

3. **Format**: `%Y-%m-%dT%H:%M:%S` (ISO 8601 with T separator, no space) throughout —
   avoids bash word-splitting when `start=2026-06-19T01:00:00` is passed as a single
   CLI token.

---

## Implementation status (as of 2026-06-22; SHAs corrected 2026-07-27)

| State | Incremental support | Signal used | SHA | Notes |
|---|---|---|---|---|
| USA | ✅ | GovInfo sitemap `lastmod` | `6d5ce6d9e` | Format string fix only — filter already existed |
| FL | ✅ | Last-action date in HTML `td[3]` | `3295ea4d0` | `SkipItem` in `BillList.process_item()`; td[3] verified against live HTML |
| WA | ⚠️ partial | `CurrentStatus/ActionDate` from GetLegislation | `5d6644b09` | **Still O(n) `GetLegislation` calls — the per-bill fetch itself is not skippable, only the 5-6 downstream calls are.** See the 2026-07-27 write-up below |
| MI | ✅ (signal still unverified) | `dateFrom=` URL param | `8db6514f5` | **Semantics still unverified as of 2026-07-27** — may be intro date not last-action date; `RUNBOOK.md` carries the same open caveat |
| UT | ⚠️ partial | `actionHistoryList[0].actionDate` | `2c1d7a0df` | Saves processing/DB-write time only, not HTTP calls — same class of gap as WA |
| MA | ✅ | `PrimarySponsor.ResponseDate` | `c211b3506` | Weak proxy — sponsor date not action date; acceptable since votes are now scraped |
| AZ | ⚠️ partial | `max(BillStatusAction.ReportDate)` | `58f006fa6` | Still O(n) API calls; skips sub-calls for unchanged bills — same class of gap as WA |
| VA | ✅ (mostly) | `max(EventDate)` from events call | `50422a94f` | Events call unavoidable (VA's list-level date fields are confirmed always null); skips 3 of 4 per-bill calls |

**SHA correction, 2026-07-27:** the SHAs above no longer match the ones originally recorded here
(`8bc4525`, `4cb3f8d`, etc.) — those commits still exist in the repo's object database but are no
longer reachable from `main`, almost certainly rewritten when `openstates-scrapers` became a
formal DDP fork on 2026-07-17 (see `PLAN-fork-management.md`). Same commit messages, same
authorship, different hashes; verified via `git log main -- scrapers/<state>/bills.py` that the
actual code is unchanged and live. `RUNBOOK.md` already had the corrected SHAs; this table did
not — now fixed. There is no longer a `ddp-incremental` branch, and nothing in
`apply-local-patches.sh` cherry-picks these anymore — see the "Deployment convention" section
below, also now stale for the same reason.

---

## Reopened 2026-07-27: the per-bill network floor (WA/UT/AZ), plus two unclosed follow-ups

Triggered by investigating why a routine WA scrape was taking ~70 minutes during an
out-of-session week with almost no legislative activity to report. The answer turned out to be
expected behavior given how this plan's own per-jurisdiction implementations work — not a
regression — but re-checking it surfaced that the underlying limitation is a real,
cross-jurisdiction pattern this plan never named as such, plus two of the plan's own explicit
follow-ups were never actually done.

### The pattern: "incremental" means different things per jurisdiction, and three of eight can't skip the per-bill fetch at all

Rechecking each `scrape()`/`scrape_bill()` in `openstates-scrapers` for whether the `start=`
cutoff check happens *before* or *after* the per-bill network fetch:

| Jurisdiction | Per-bill fetch skippable when unchanged? | Date signal used | Source |
|---|---|---|---|
| **FL** | Yes — filters before any per-bill fetch | Last-action date already in the bill-list HTML row | `bills.py` `BillList.process_item()` |
| **US federal** | Yes — filters before any per-bill fetch | `lastmod` in the govinfo sitemap XML (bulk, already fetched) | `bills.py` `parse_bill_list()` |
| **MI** | Yes — server-side; unchanged bills never even get listed | `dateFrom=` passed as a query param to MI's own search endpoint | `bills.py` `scrape()` |
| **MA** | Yes — filters before any per-bill fetch | Sponsor `ResponseDate` in one bulk JSON list call | `bills.py` `scrape_bill_list()` |
| **VA** | Partial — skips 3 of 4 per-bill calls (versions/sponsors/votes), not the 4th (events) | `max(EventDate)` from the events call, itself unavoidable | `bills.py` scrape loop |
| **WA** | **No** — one full `GetLegislation` fetch per bill is unavoidable; only the 5-6 *downstream* calls (sponsors/actions/hearings/votes/etc.) are skipped | `CurrentStatus/ActionDate`, only available after the fetch | `bills.py` `scrape_bill()` |
| **UT** | **No** — one full per-bill JSON fetch is unavoidable (already an all-in-one response, so nothing extra beyond parsing/DB-write time is saved) | `actionHistoryList[0].actionDate`, only available after the fetch | `bills.py` `scrape_bill_details_from_api()` |
| **AZ** | **No** — one full per-bill JSON fetch is unavoidable; downstream sponsor/version/vote sub-calls are skipped | `max(BillStatusAction.ReportDate)`, only available after the fetch | `bills.py` `scrape_bill()` |

For WA/UT/AZ this is structural: their bill-*list* endpoints carry no date field at all, so
there's nothing to filter on until each bill's own detail is individually fetched. VA's list
endpoint has 5 date fields but this plan's own 2026-06-22 research (Part 9 above) already
confirmed all of them are null for every bill, and every guessed date-range/server-side-filter
endpoint either has no effect or 404s — so VA is stuck with at least the one events call per bill
too, same root cause as WA/UT/AZ, just with a smaller remaining bill count.

This plan's original per-state write-ups (Parts 4, 6, 8 above) already *said* this in each
section's own "Impact" note (e.g. WA: "One `GetLegislation` call per bill is unavoidable") — the
gap wasn't a wrong technical claim, it's that nothing tied these three together as one
cross-cutting property worth tracking as its own open item, so it read as three independent
minor caveats rather than a real, un-closed part of "incremental scraping."

### Concrete impact, confirmed live 2026-07-27

WA's biennium has ~3,400 bills. At `SCRAPELIB_RPM=60` (~1 request/sec), that's a hard floor of
~55-60 minutes for the scrape phase alone, regardless of how many bills actually changed — an
out-of-session week with zero real legislative activity pays this same cost every night, because
WA is one of the three **daily**-scraped jurisdictions. UT/AZ pay the same *shape* of cost but are
**weekly**-scraped secondary states, so it's less visible day-to-day; VA is both weekly-scraped
and has the shortest active bill list of the four (its 2026S1 special session was only 273
bills), so it's the least urgent — consistent with this plan's original per-jurisdiction urgency
ranking ("Implementation order" below), which is still accurate today.

### Two follow-ups this plan named and never closed

1. **WA's WSDL upgrade path was never checked.** "Implementation order" step 5 below says to
   "check WSDL for date-range endpoint upgrade" alongside shipping the WA filter — that check
   never happened. Concretely: verify whether WA's SOAP API
   (`http://wslwebservices.leg.wa.gov/legislationservice.asmx`) exposes a
   `GetLegislativeStatusChangesByDateRange`-style operation. If it does, it would return only the
   bill IDs with status changes in a date range, eliminating the O(n) `GetLegislation` calls
   entirely instead of just skipping the downstream sub-calls — the only one of the three
   (WA/UT/AZ) with a plausible path to removing the per-bill-fetch floor rather than just working
   around it, since UT's and AZ's per-bill calls are already single all-in-one responses with no
   equivalent lighter-weight endpoint to check for.
2. **MI's date signal is still unverified.** The Implementation status table above has carried
   "semantics unverified — may be intro date not last-action date" since 2026-06-22; `RUNBOOK.md`
   still lists the same open caveat today. Nobody has forced a full MI scrape and diffed counts
   against a normal incremental run to settle this, per this plan's own suggested verification
   method ("If MI incremental runs return unexpectedly few bills, force a full scrape and compare
   counts").

### Practical takeaway for scheduling/monitoring

WA/UT/AZ/VA's nightly runtime has a floor set by each jurisdiction's *total* bill count, not by
legislative activity — an out-of-session run taking as long as an in-session one is expected
behavior, not a sign of a stuck or misbehaving scrape. Any future "this run is taking too long"
alert threshold should account for this rather than assuming session status predicts runtime.
`PLAN-open-states.md` §2.6 has a short pointer to this section for readers coming from that plan.

**Not yet done / next steps:**
- Check WA's WSDL for a date-range-capable operation (see above); if one exists, scope the
  scraper change to use it instead of per-bill `GetLegislation` calls.
- Force a full MI scrape and diff against a normal incremental run to settle the
  intro-date-vs-last-action-date question.
- No action proposed for UT/AZ specifically — both already have single all-in-one per-bill
  responses with no cheaper alternative identified, so there's no equivalent upgrade path to
  chase the way there might be for WA.

---

## Reopened 2026-07-28: the UT/VA skip pattern was deleting data, not just saving time

Triggered by investigating why UT had zero archived bill documents (`PLAN-open-states.md`'s UT
finding). The original diagnosis blamed a 2025 site-redesign scraper gap — that was wrong,
corrected the same day after actually running the scraper live. **The real bug lives in this
plan's own `start=` implementation**, and the table above's "VA: Partial — skips 3 of 4 per-bill
calls" and "UT: one full per-bill JSON fetch" rows were describing the *symptom* of something
worse than an efficiency tradeoff.

### The bug

UT's and VA's per-bill `start=` check both follow the same shape: fetch the bill's detail data,
check whether its last action predates the cutoff, and if so, **return/yield early** — but by
that point in both functions, a `Bill` object already exists (UT: passed in by the caller; VA:
constructed and already given its actions). The early exit skipped populating the *rest* of the
bill (UT: versions, documents, sponsorships, actions; VA: versions, sponsorships, votes,
abstracts) — but both still handed that now-partial `Bill` to the importer. `openstates-core`'s
importer (`importers/base.py`) treats "the new scrape found zero of these related items" as
"delete whatever's already in the database" for that bill. Net effect: **every incremental run
against an unchanged bill silently deleted that bill's already-good data**, for as long as either
jurisdiction's `start=` filtering has existed.

**Confirmed real damage, both jurisdictions:**
- **UT**: zero actions, zero sponsorships, zero versions across all 1,021 tracked bills. The
  incremental filter was added 2026-06-30 (`2c1d7a0d`); a clean full scrape on 2026-06-14 had
  populated everything correctly, and it's been getting wiped back out ever since.
- **VA**: the regular 2026 session (3,637 bills) is intact, but the 2026S1 special session — 300
  bills, gone quiet since early May — has zero versions and zero sponsorships across all 300.
  Double-checked the bill count itself against the public OpenStates API: exactly 300 there too,
  so the bill records are correct, only their content was deleted.

**Every other jurisdiction was audited and is clean.** The distinguishing factor isn't whether a
jurisdiction *has* `start=` filtering (all 8 do) — it's *where* the skip decision happens relative
to `Bill` construction:

| Jurisdiction | Skip mechanism | Safe? |
|---|---|---|
| FL, MA | Filters the bill *list* before any `Bill` object exists (`SkipItem` / `continue` in list-building) | Yes |
| MI | Filters server-side (`dateFrom=` query param) — stale bills never appear in the list at all | Yes |
| US federal | Only calls the per-bill parse function at all for bills newer than the cutoff | Yes |
| WA, AZ | Early `return` happens *before* `Bill(...)` is constructed in the per-bill function | Yes |
| **UT** | Early `return` inside a sub-function, *after* the caller already has a `Bill` to populate | **No — fixed, PR #10** |
| **VA** | `Bill(...)` constructed and actions added *before* the cutoff check; used to `yield` anyway | **No — fixed, PR #11** |

### The fix

Both now skip the bill entirely rather than yielding a partially-populated one:
- **UT** (`openstates-scrapers` PR #10): `scrape_bill_details_from_api()`'s early return now
  returns `True`, captured via `skip = yield from self.scrape_bill_details_from_api(...)` in
  `scrape_bill()`, which returns before ever reaching `yield bill` when `skip` is true.
- **VA** (`openstates-scrapers` PR #11): the skip branch is now a plain `continue` instead of
  `bill.add_source(...); yield bill; continue` — the bill is never yielded at all.

Both verified live: instantiating the real scraper class against real bills, the skip path now
yields nothing, and the normal (non-skip) path still populates versions/sponsorships exactly as
before.

### Still needed — not yet done

**Fixing the code stops the bleeding; it doesn't restore what's already gone.** An incremental
scrape only looks at bills with activity since the last cutoff — it can't backfill a bill whose
last action is years (or, for VA's 2026S1, months) in the past. Both jurisdictions need a genuine
**full scrape** (no `start=`) once the fixes are merged and synced to production:
- `os-update ut bills` / equivalent full-scrape invocation for UT, then re-run
  `os-text-extract archive ut` to confirm it now finds and archives real documents.
- A full scrape of VA's `2026S1` session specifically (the regular 2026 session doesn't need it).

**Broader lesson for any future jurisdiction-specific `start=` work:** the safe pattern is "skip
before creating/populating a `Bill`, or skip by simply not yielding it" — never partially
populate a `Bill` and yield it anyway on the skip path. Worth a one-line callout in this plan's
"Standard pattern" section above for anyone implementing this for a 9th jurisdiction later.

---

## Reopened 2026-07-30: import only happens once, at the very end — a killed scrape loses everything

Triggered by a manual FL/MA backfill (chasing 162 FL bills missed during a WAF block) that got
killed when the Claude Code session that launched it closed — the launching process wasn't
detached from the session, a separate and now-fixed problem. What it surfaced is more important
than the detachment bug itself: **neither run had written a single row to Postgres**, even though
FL had scraped 213 bills and MA 473 to local JSON before dying, and restarting both runs silently
**deleted** that JSON — none of it was ever recoverable. This plan's name is "incremental
scraping," and it was reasonable to assume — a teammate did, out loud — that meant incremental
*ingestion*. It doesn't. Nothing in this plan, or anywhere else in this codebase, changes when
scraped data reaches Postgres. That's a separate, unaddressed gap, and it's worse than "batched
until the end" — it's "batched until the end, in one transaction, on top of a data directory that
gets wiped the moment anyone retries."

### The bug: three compounding gaps, none of them new, none of them touched by this plan

All three live in `openstates-core` (upstream, unpatched by DDP) and `run-scrape.sh`, and none of
them care whether the scrape itself was full or incremental:

1. **`run-scrape.sh` calls `os-update --scrape` and `os-update --import` as two separate process
   invocations**, scrape fully first, then import — not a single pipeline where scraping a bill
   and importing it are one step.
2. **`do_scrape()` (`openstates-core/openstates/cli/update.py:81-82`) deletes every existing JSON
   file in the jurisdiction's data directory before writing anything new:**
   ```python
   for f in glob.glob(datadir + "/*.json"):
       os.remove(f)
   ```
   Confirmed live 2026-07-30: after FL and MA's original runs died mid-scrape (213 and 473 bill
   files respectively, all pre-import), restarting both jobs left every `bill_*.json` in
   `_data/fl/` and `_data/ma/` timestamped from the *restart*, none from the original run. The
   scraped work was not resumed; it was silently destroyed by the next `--scrape` invocation's own
   cleanup step.
3. **`do_import()` (`update.py:284`) wraps the entire import for one invocation — jurisdiction,
   every bill, every vote event, every event — in a single `with transaction.atomic():` block.**
   A single bad record anywhere in that batch rolls back everything else in the same call, not
   just the offending row.

Put together: a scrape that dies before its one `--import` call reaches `do_import()` loses that
run's data completely, with no partial credit at the file layer (next scrape wipes it) or the DB
layer (there was never a transaction to partially commit). The **only** existing mitigation is
`_cache/`, the raw HTTP response cache used by `--fastmode` — it survives a restart and avoids
re-hitting the legislature's website, but it does nothing for the parsed `Bill` objects, which
have to be rebuilt from that cache from scratch.

**This was not something this plan (or any other) claimed to fix.** `PLAN-incremental-scraping.md`
's own scope, top to bottom, is which bills get *scraped* on a given run (skip bills unchanged
since `start=`) — it never touches the scrape→JSON→import→Postgres handoff. The confusion is
understandable: "incremental scraping" and "incremental ingestion" sound like the same feature.
They aren't, and until now nobody had scoped the second one at all.

### Confirmed: repeat imports are safe (this fix's central assumption)

Before proposing anything that calls `--import` more than once per run, it's worth confirming that
doing so doesn't corrupt or duplicate data. Checked directly against
`openstates-core/openstates/importers/base.py`:

- `BaseImporter.import_item()` looks up each incoming record by natural key
  (`self.get_object(data)`); if it exists, fields are diffed and only saved on an actual change
  (`what = "update"`); if it doesn't, it's inserted. There is no import-once assumption baked in —
  every existing nightly run already calls `import_directory()` on "whatever's currently in the
  directory," this plan just proposes calling it on a *growing* directory, more often.
- The `DuplicateItemError` guard (`obj.id in self.json_to_db_id.values()`) only fires *within* a
  single `import_data()` call (two different JSON files resolving to the same DB row in the same
  batch) — `json_to_db_id` is reset at the start of every call, so it says nothing about, and does
  not conflict with, calling import repeatedly across separate invocations.
- `do_import()`'s `transaction.atomic()` wraps one *invocation*, not the whole run — so calling
  `--import` N times across a long scrape produces N independent transactions. A failure in sweep
  #12 rolls back only sweep #12's batch; sweeps #1-11 already committed and stay committed. This
  is the actual mechanism that turns "one all-or-nothing multi-hour transaction" into "bounded,
  recoverable chunks."

### PM review (2026-07-30) — verdict `high_risk`, do not ship the first draft

Sent the design above (before the "The fix" subsection was revised to what follows) to
`/pm-review`. Verdict: **`high_risk`, do_not_ship_yet.** Three findings changed the design, not
just the write-up:

1. **Files are written `open()` → `json.dump()` → `close()`, not staged and renamed into place.**
   A sweep's `glob()` can catch a bill file mid-write. `json.load()` on a half-written file raises,
   and because `do_import()` wraps the *entire* directory's import in one transaction, that one
   bad read fails every file in that sweep — and, since nothing removes the bad file, **every
   subsequent sweep too**, indefinitely. The original draft's "sweeps #1-11 stay committed even if
   #12 fails" claim is only true for a transient failure; a stuck-forever poison file breaks the
   stated loss-bound entirely. Needed a real fix, not just a caveat.
2. **The recovery-import snippet (A) defeated its own purpose on failure.** It logged a warning and
   *proceeded with the rescrape anyway* — which wipes the directory it just failed to save. Fixed
   below: recovery-import failure now blocks the rescrape and alerts, instead of silently finishing
   the job the recovery step existed to prevent.
3. **`kill "$SWEEP_PID"; wait` is not a real lock.** If the sweep loop is killed while its child
   `os-update --import` is mid-flight, the signal doesn't necessarily reach or wait on that child —
   the final import could start while a sweep's import is still running, both writing to the same
   directory's data. Fixed below with the same `mkdir`-based mutex pattern this file already uses
   for `SCRAPE_MARKER_DIR` (atomic, no missing-CLI-tool risk — `flock` isn't guaranteed present on
   macOS the way it is on Linux).

Also flagged, not yet resolved (see "Open questions," carried forward): this changes when a
jurisdiction's data becomes visible in Postgres, from "all at once when the whole scrape finishes"
to "incrementally, over the run" — a product-visible change for anything reading live, not just an
internal implementation detail, and worth a explicit yes before shipping rather than assuming it's
fine because it sounds like a pure improvement.

### PM review round 2 (2026-07-30) — still `high_risk`, but on the lock/quarantine plumbing, not the design

Sent the revision above back for a second pass. Verdict: **`high_risk`, do_not_ship_yet** again,
but every finding this time was a concrete bug in the round-1 fix's own bash, not a new design
concern:

1. **`with_import_lock` returned success (`0`) when it *skipped* due to contention.** Fine for a
   best-effort sweep; not fine for recovery/final import, which could "succeed" without having
   imported anything and then proceed to rescrape/wipe, or finish the run reporting a clean exit
   with the last window never actually imported.
2. **The final import reused the sweep's age-filtered staging copy**, which would exclude the
   files written right before the scraper exited — undercutting the "final import catches
   everything since the last sweep" claim. Once `scrape_attempt()` has returned there's no writer
   left, so the final import doesn't need staging or an age filter at all — it can read
   `$STATE_DATADIR` directly.
3. **The quarantine `grep` searched for the original `$STATE_DATADIR` path**, but sweeps import
   from the *staged* copy — the importer's own error output would reference the staged path, so the
   pattern would never match and quarantine would silently never fire.
4. **`find ... -mmin +0.08`** — fractional-minute `find` semantics untested on this deployment's
   actual `find`; not worth the risk when a `stat`-based loop is simple and already verified working
   on this exact machine.
5. **`mkdir "$IMPORT_LOCK_DIR"`** would fail (and, per bug 1, be silently treated as "lock busy") if
   its parent directory doesn't exist yet — `/tmp/ddp-openstates-import-locks` is never created
   anywhere in the original snippet.

**Triaged the rest of the review's recommendations rather than applying all of it** — the reviewer
also suggested full lock-ownership metadata (start time, command, hostname/session), a
metrics/dashboard layer (files staged, files imported, skipped-due-to-lock, quarantine counts,
etc.), and an exhaustive stale-lock/orphan-process test matrix. Judgment call: those are reasonable
*eventually*, but disproportionate for closing the five concrete bugs above. Fixed below with the
minimum that actually closes each one — a single PID field (not a full metadata record) is enough
for the trap to know whether it owns the lock it's about to remove; a blocking acquire with a
timeout (not a distributed-lock system) is enough to make "recovery/final either really imported or
really failed" true; one added test per fixed bug (not a full matrix) is enough to prove each fix
concretely, in the existing "Testing plan" section.

### PM review round 3 (2026-07-30) — still `high_risk`: one real hole in round 2's own fix, plus a legitimate simplification (not more machinery)

Sent round 2's revision back with an explicit ask to guard against over-engineering this time —
confirm the round-2 bugs are actually closed, and flag anything that's grown more complex than the
failure mode it protects against actually warrants. Verdict: **`high_risk`, do_not_ship_yet**, but
the shape of the findings changed again — one is a real, important bug in round 2's own fix; the
right response to the other is to *cut* code, not add more:

1. **`$$` doesn't do what round 2's ownership fix assumed.** `sweep_import` runs as a *backgrounded
   function*, not a true subshell with its own `$$` — in bash, `$$` inside a background job still
   reports the **top-level script's** PID, not the job's own. So `echo "$$" > .../pid` from inside
   the sweep loop writes the *same* value the main script itself would write, and the EXIT trap's
   `[ "$(cat pid)" = "$$" ]` check is always true regardless of which of the two actually holds the
   lock — round 2's fix for "the trap can remove a lock it doesn't own" didn't actually change
   anything. Real bug, cheap fix: use `$BASHPID` (the actual running process's PID, distinct for a
   backgrounded job) everywhere the lock records and checks ownership, not `$$`.
2. **A hard-killed process (`SIGKILL`, not caught by any trap) leaves the `mkdir` lock permanently
   held** — nothing ever runs `release_import_lock` for it, and there's no path back. Given this
   fix exists *because* a process got killed out from under a running scrape, this isn't a
   theoretical edge case — it needs handling, but a proportionate one: check whether the PID
   recorded in the lock is still alive (`kill -0`) before treating a failed `mkdir` as "someone else
   legitimately holds this"; if it's dead, the lock is stale and safe to reclaim.
3. **Automatic quarantine (moving the live source file out of `$STATE_DATADIR` on a sweep failure)
   was itself unsafe, for two compounding reasons the reviewer named:** the `grep` scans the
   *entire, cumulative* `scraper.log`, so a genuinely unrelated failure (DB hiccup, transient error
   with no file path at all) could still match some *older* staged-path mention and quarantine an
   innocent, already-valid bill; and moving the live file at all, during an active scrape, risks
   relocating a file the scraper still has open, permanently hiding a bill that was actually about
   to finish writing correctly. Both are real ways this fix could **cause** the exact kind of
   silent, hard-to-detect data loss it exists to prevent.

**On (3): the fix is to remove the mechanism, not harden it.** The reviewer's own suggested
mitigations for it — a per-sweep-scoped log capture, confirmed-error-signature matching before
quarantining, revalidating a file as "still bad" before moving it — are reasonable but add real
complexity to close a hole that doesn't need to exist in the first place. Sweeps never need to
touch the live file at all: excluding a suspect file from *this run's staging* only (an in-memory
list, never written to disk, never touching `$STATE_DATADIR`) gets the same practical benefit —
one bad file stops blocking every future sweep — without ever risking the live directory. A file
that's *actually* permanently bad (not just transiently mid-write) gets one more real attempt at
the final import, which already reads `$STATE_DATADIR` directly and already alerts on failure via
the existing `on_failure` path — identical to how a bad file fails a scrape today, just now with
every *other* bill from the run already safely in Postgres via the sweeps that succeeded around it.
No new alerting path, no quarantine directory, no ownership question about who reviews it — this is
strictly less code than round 2's version, not more, and it's what closes the review's actual
concern.

*Declined again, consistent with rounds 1-2's triage, now that (3) removes the need for most of
it:* per-sweep log capture and error-signature matching (moot — nothing is being auto-moved
anymore, so mis-identifying "the bad file" only costs one extra retry next cycle, not a misfiled
bill); canary promotion metrics as a formal gate (still an open, tunable-later item, not a
correctness fix).

### The fix, revised again (round 3): `$BASHPID` for lock ownership, stale-lock reclaim, in-memory sweep exclusion instead of quarantine

**Goal:** unchanged. **Shared setup** — same two lock modes as round 2, now using `$BASHPID` (fixes
finding 1) and reclaiming a lock whose recorded PID is no longer alive (fixes finding 2):

```bash
STATE_DATADIR="$SCRAPED_DATA_DIR/$STATE"
IMPORT_FLAGS=""
[ "$STATE" = "mi" ] || [ "$STATE" = "fl" ] || [ "$STATE" = "va" ] && IMPORT_FLAGS="--allow_duplicates"

IMPORT_LOCK_DIR="/tmp/ddp-openstates-import-locks/$STATE"
mkdir -p "$(dirname "$IMPORT_LOCK_DIR")"
IMPORT_LOCK_HELD=0

acquire_import_lock() {
    if mkdir "$IMPORT_LOCK_DIR" 2>/dev/null; then
        echo "$BASHPID" > "$IMPORT_LOCK_DIR/pid"  # $BASHPID, not $$ — distinct per backgrounded job (fix 1)
        IMPORT_LOCK_HELD=1
        return 0
    fi
    # mkdir failed — check whether the recorded holder is actually still alive before
    # treating this as real contention (fix 2: a SIGKILL'd process never releases the lock).
    local holder; holder=$(cat "$IMPORT_LOCK_DIR/pid" 2>/dev/null)
    if [ -n "$holder" ] && ! kill -0 "$holder" 2>/dev/null; then
        log "Import lock for $STATE held by dead pid $holder — reclaiming"
        rm -rf "$IMPORT_LOCK_DIR"
        mkdir "$IMPORT_LOCK_DIR" 2>/dev/null && { echo "$BASHPID" > "$IMPORT_LOCK_DIR/pid"; IMPORT_LOCK_HELD=1; return 0; }
    fi
    return 1
}
release_import_lock() {
    [ "$IMPORT_LOCK_HELD" = "1" ] || return 0
    rm -rf "$IMPORT_LOCK_DIR"
    IMPORT_LOCK_HELD=0
}
try_import_lock() {  # $1 = command to eval; return 2 if busy (distinct from the command's own exit code)
    acquire_import_lock || return 2
    eval "$1"; local rc=$?
    release_import_lock
    return $rc
}
require_import_lock() {  # $1 = command to eval; blocks up to LOCK_WAIT_TIMEOUT_SECS, then fails
    local waited=0 timeout="${LOCK_WAIT_TIMEOUT_SECS:-180}"
    until acquire_import_lock; do
        [ "$waited" -ge "$timeout" ] && {
            log "ERROR: timed out after ${timeout}s waiting for import lock for $STATE (held by pid $(cat "$IMPORT_LOCK_DIR/pid" 2>/dev/null))"
            return 1
        }
        sleep 5; waited=$((waited + 5))
    done
    eval "$1"; local rc=$?
    release_import_lock
    return $rc
}
```

**A. Pre-scrape recovery import** — unchanged from round 2: `require_import_lock`, blocks the
rescrape and alerts via `on_failure` on any real failure (import failure or lock timeout).

**B. Periodic import sweep — no more quarantine directory or `mv`.** A failed sweep just excludes
the suspected file from staging for the rest of *this run* (in-memory, resets on the next
`run-scrape.sh` invocation — no persistence needed, since a truly bad file will fail the final
import too and alert exactly as today):

```bash
SWEEP_INTERVAL_SECS="${SWEEP_INTERVAL_SECS:-120}"
SWEEP_STAGING_DIR="/tmp/ddp-openstates-sweep-staging/$STATE"

sweep_import() {
    declare -A EXCLUDED_FROM_STAGING  # basename -> 1; in-memory only, this process's lifetime
    while true; do
        sleep "$SWEEP_INTERVAL_SECS"
        [ -d "$STATE_DATADIR" ] || continue

        rm -rf "$SWEEP_STAGING_DIR"; mkdir -p "$SWEEP_STAGING_DIR/$STATE"
        CUTOFF_EPOCH=$(( $(date +%s) - 5 ))
        for f in "$STATE_DATADIR"/*.json; do
            [ -e "$f" ] || continue
            [ -n "${EXCLUDED_FROM_STAGING[$(basename "$f")]:-}" ] && continue
            mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null)
            [ -n "$mtime" ] && [ "$mtime" -lt "$CUTOFF_EPOCH" ] && cp "$f" "$SWEEP_STAGING_DIR/$STATE/"
        done

        rc=0
        try_import_lock "\$OS_UPDATE $STATE --import $IMPORT_FLAGS --datadir $SWEEP_STAGING_DIR --cachedir \$CACHE_DIR >> \"$LOG_DIR/scraper.log\" 2>&1" || rc=$?
        if [ "$rc" = 2 ]; then
            log "Import already in progress for $STATE — skipping this sweep cycle"
        elif [ "$rc" != 0 ]; then
            # Best-effort: exclude the most-recently-referenced staged file from future sweeps
            # this run, so one bad bill doesn't block every later valid one. Nothing is moved or
            # deleted — worst case of a wrong guess here is one extra bill waits until final
            # import, not a bill silently vanishing from the live directory.
            BAD_STAGED=$(grep -oE "$SWEEP_STAGING_DIR/$STATE/[A-Za-z_]+_[0-9a-f-]+\.json" "$LOG_DIR/scraper.log" | tail -1)
            [ -n "$BAD_STAGED" ] && EXCLUDED_FROM_STAGING[$(basename "$BAD_STAGED")]=1
            log "WARNING: periodic import sweep failed for $STATE — excluding ${BAD_STAGED:-unknown file} from staging until final import"
        fi
    done
}
sweep_import &
SWEEP_PID=$!
trap 'kill "$SWEEP_PID" 2>/dev/null; wait "$SWEEP_PID" 2>/dev/null;
      [ "$(cat "$IMPORT_LOCK_DIR/pid" 2>/dev/null)" = "$BASHPID" ] && rm -rf "$IMPORT_LOCK_DIR"' EXIT
```

Sweep failures still don't call `on_failure` on the first miss — log, exclude, retry next cycle.
Escalate to the existing Slack/CAMS path only after 3 consecutive real failures (`try_import_lock`
returning `2` — busy, not broken — doesn't count toward that streak).

**C. Final import** — unchanged from round 2: reads `$STATE_DATADIR` directly (no staging, no
exclusion list — everything gets a real attempt), under `require_import_lock`. **Its failure or a
lock-wait timeout hits the exact same `on_failure`/Slack/CAMS/exit path as any other import failure
today** — stated explicitly per review ask; mechanically this already falls out of `set -e` + the
existing `trap ... ERR`, nothing new to build. If a file excluded by every sweep this run is
genuinely corrupt, this is where it surfaces and alerts — same outcome as an unfixed bad file
causes today, just now scoped to one bill instead of the whole run's data.

**D. Locking** — the `mkdir`+PID-file mutex, now correctly attributing ownership via `$BASHPID`
(fix 1) and able to reclaim a lock abandoned by a hard-killed process (fix 2).

### Non-goals (deferred, not dismissed)

- **True per-bill streaming import from inside the scraper process itself.** Would require
  patching `openstates-core`'s scrape internals (not just `run-scrape.sh`), opening a live Django/DB
  connection for the full duration of a multi-hour scrape, and reworking `do_import()`'s
  transaction to be per-object instead of per-directory. Bigger surface, more risk (a long-held DB
  connection across a scrape that can run 30+ hours), and the periodic-sweep design gets the
  practical loss-bound down to minutes without any of that. Worth revisiting only if a 2-minute
  loss window ever proves insufficient in practice.
- **Fixing `do_scrape()`'s unconditional directory wipe upstream.** The pre-scrape recovery import
  (A) — now blocking on failure — makes this safe in practice, so patching the wipe itself isn't
  required for this fix.
- **A stronger atomic-write guarantee inside the scraper (write-to-temp + rename).** The staging
  copy + age filter in (B) makes a mid-write read very unlikely without touching scraper internals;
  a true fix (temp file + `os.rename()`, which is atomic on the same filesystem) would remove the
  risk entirely but requires an `openstates-core` patch. Worth doing later as defense in depth, not
  a blocker for this fix.

### Open questions for review

- **Product sign-off on partial-run visibility.** This changes a jurisdiction's data in Postgres
  from "consistent snapshot, updated once when the whole scrape finishes" to "updated
  incrementally throughout a multi-hour run." Anything reading this data live (`api-v3`,
  dashboards) should be confirmed fine with seeing a jurisdiction mid-update, not assumed fine
  because the change sounds like a pure reliability win.
- **DB load from resweeping.** Even staged/filtered, each sweep still touches every
  already-imported bill in the directory (a no-op `get_object` lookup, no write). For FL's
  ~2,000-bill session at a 120s cadence over 30+ hours, that's up to ~900 sweeps × up to 2,000
  lookups. Phase 1 ships this as-is (simplest, correct); Phase 2 fast-follow if load is real:
  only stage files modified since the last sweep's own marker (`find -newer <marker touched each
  cycle>`), which the natural-key upsert model handles just as safely, just cheaper.
- **Sweep interval value.** 120s is a starting proposal. Needs a measured answer, not a guess: how
  long does a full `--import` pass actually take for FL/MA at peak size (must stay well under the
  interval or sweeps start backing up), and what DB load can the Mac Studio's Postgres instance
  absorb during FL/USA's longest concurrent runs.
- **Rollout gating.** Given the `high_risk` verdict on the first draft, ship behind an explicit
  opt-in flag (`SWEEP_IMPORT_ENABLED=1`, default off) and canary on the smallest/lowest-risk
  jurisdiction (VA or UT) first, with sweep duration/outcome logged per cycle, before enabling for
  FL/MA/USA where the incident risk (and the DB load question above) is highest.
- **`LOCK_WAIT_TIMEOUT_SECS` value.** 180s is a starting proposal for `require_import_lock`, same
  status as the 120s sweep interval — a guess to be replaced with a measured one once real sweep
  durations for FL/MA are known (the timeout needs to comfortably exceed one real sweep's runtime,
  or the final import will spuriously time out on every normal run).

*Removed as an open question after round 3, not just deferred:* what to do about quarantined files
sitting unreviewed — there's no quarantine directory anymore (see round 3), so nothing accumulates
that needs a review loop. A file excluded from staging this run either imports fine on the final
pass or fails it exactly like any other bad-file failure does today.

*Deliberately left as-is, not chased further, after rounds 2-3:* full lock-ownership metadata beyond
a PID (start time, command, hostname), a dedicated sweep metrics/dashboard layer (files staged,
skipped-due-to-lock counts, etc.) beyond the existing per-cycle log lines, and per-sweep-scoped log
capture with confirmed-error-signature matching (moot once sweeps stopped moving files — see round
3). All reasonable future hardening, none required to make this fix safe to ship.

### Testing plan (added per review — not in the original draft; extended after rounds 2-3)

Failure-injection, not just unit-level: kill the scrape process at each of these points and verify
(a) expected bills are in Postgres, (b) no corruption, (c) the next run behaves correctly —
- Mid-scrape, before any sweep has run.
- Mid-scrape, immediately after a sweep succeeds.
- During a sweep's `--import` call itself.
- Between the sweep-loop `kill` and the final import call.
- During the final import call.
- During the pre-scrape recovery import (verify it blocks the rescrape as designed, doesn't wipe).

Plus, one test per fixed bug:
- Hand-craft a malformed `bill_*.json` mid-run; confirm it's excluded from staging (not moved or
  deleted — still present in `$STATE_DATADIR`) within one sweep cycle, that later sweeps for other
  bills succeed, and that the final import still attempts it and fails/alerts exactly as an
  unfixed bad file would today.
- Hold the import lock artificially (background `mkdir` + sleep) while the final import runs;
  confirm it blocks and retries rather than skipping, and confirm it fails loudly (alerts) if held
  past `LOCK_WAIT_TIMEOUT_SECS` instead of silently reporting success.
- `kill -9` `run-scrape.sh` itself while it holds the lock (mid `require_import_lock`); confirm the
  *next* invocation for the same `$STATE` detects the recorded PID is dead and reclaims the lock
  rather than blocking for the full timeout every time.

### Files changed (proposed)

| File | Change |
|---|---|
| `run-scrape.sh` | Shared `IMPORT_FLAGS` + two-mode lock (`try`/`require`) setup using `$BASHPID` with stale-lock reclaim; pre-scrape recovery import via `require_import_lock`, blocks on failure (A); background sweep loop via `try_import_lock` with staged/`stat`-age-filtered import + in-memory exclusion list (no file moves) (B); final import reads the live directory directly via `require_import_lock` (C, D) |

No `openstates-core` or `openstates-scrapers` changes required — this is entirely a `run-scrape.sh`
orchestration fix, calling the existing `os-update --import` CLI more often instead of patching
what it does internally.

---

## Prerequisite fix (ship first, independently)

**File:** `run-scrape.sh` lines 55–61

Add `fl` to the `--allow_duplicates` guard (same pagination-overlap bug as MI #5697;
FL import currently fails with `DuplicateItemError` for HB 6009):

```bash
if [ "$STATE" = "mi" ] || [ "$STATE" = "fl" ]; then
    $OS_UPDATE "$STATE" --import --allow_duplicates $DIR_FLAGS \
        >> "$LOG_DIR/scraper.log" 2>&1
```

---

## Implementation

### Part 1 — Shell timestamp layer (`run-scrape.sh`)

**Key naming:** `$STATE` + `$SESSION_ARG` with spaces/`=` replaced by `_`:
- `fl session=2026` → `logs/last-run/fl_session_2026.ts`
- `usa session=119 chamber=lower` → `logs/last-run/usa_session_119_chamber_lower.ts`
- `wa` (no session arg) → `logs/last-run/wa.ts`

**Add after line 6 (`SESSION_ARG=...`):**

```bash
LAST_RUN_DIR="$LOG_DIR/last-run"
SCRAPE_KEY=$(echo "${STATE}${SESSION_ARG:+ $SESSION_ARG}" | tr ' =' '__')
TS_FILE="$LAST_RUN_DIR/${SCRAPE_KEY}.ts"

INCREMENTAL_FLAG=""
if [ -f "$TS_FILE" ]; then
    LAST_RUN=$(cat "$TS_FILE")
    START_ARG=$(python3 -c "
import datetime, sys
try:
    dt = datetime.datetime.strptime('$LAST_RUN', '%Y-%m-%dT%H:%M:%S')
    print((dt - datetime.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S'))
except Exception:
    sys.exit(0)
" 2>/dev/null)
    if [ -n "$START_ARG" ]; then
        INCREMENTAL_FLAG="start=$START_ARG"
        echo "[$(date)] Incremental run: start=$START_ARG" | tee -a "$LOG_DIR/scraper.log"
    fi
fi
```

Append `$INCREMENTAL_FLAG` (unquoted — no spaces in value) to both `os-update` calls
on lines 42 and 47. Remove the `case "$STATE"` guard — once all scrapers support
`start=`, it's passed universally. (Scrapers that don't implement `start=` will just
receive an unexpected kwarg and fail loudly, making it easy to detect missing
implementation during rollout. Alternatively, keep the guard and expand it state by
state as each scraper is patched.)

**Add after the import log line (line 63):**

```bash
mkdir -p "$LAST_RUN_DIR"
date -u +%Y-%m-%dT%H:%M:%S > "$TS_FILE"
```

Timestamp is written only on successful import (`set -e` trap prevents writing on
failure), so a failed run preserves the previous checkpoint.

---

### Part 2 — USA scraper (1-line fix)

**File:** `openstates-scrapers/scrapers/usa/bills.py:102`

```python
# before
start = datetime.datetime.strptime(start, "%Y-%m-%d %H:%I:%S")
# after
start = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
```

Update comment on line 99:
```python
# to scrape everything UPDATED after a given date/time, start="2020-01-01T22:01:01"
```

Mechanism (already implemented, lines 137–150): iterates GovInfo sitemap, only fetches
bills where `lastmod > start`. Skips ~95% of the 10k bills on a daily incremental run.

---

### Part 3 — FL scraper

**File:** `openstates-scrapers/scrapers/fl/bills.py`

**3a — `FlBillScraper.scrape()` (line 896):** add `start=None`, parse it, pass to BillList:

```python
def scrape(self, session=None, start=None):
    ...
    start_dt = None
    if start:
        try:
            start_dt = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            self.warning(f"Invalid start= '{start}', doing full scrape")

    def do_scrape_with_retry():
        bill_list = BillList({
            "session": session,
            "house_session_number": house_session_number,
            "start": start_dt,  # None = full scrape
        })
        yield from self._process_bill_list(bill_list)
```

**3b — `BillList.process_item()` (after line 168):** add SkipItem filter.

Add `SkipItem` to the existing spatula import on line 16:
```python
from spatula import HtmlPage, HtmlListPage, XPath, SelectorError, PdfPage, URL, SkipItem
```

After extracting `title`:
```python
start = self.input.get("start")
if start is not None:
    last_action_cell = item.xpath("string(../following-sibling::td[3])").strip()
    date_matches = re.findall(r"\d{1,2}/\d{1,2}/\d{4}", last_action_cell)
    if date_matches:
        try:
            last_action = datetime.datetime.strptime(date_matches[0], "%m/%d/%Y")
            if last_action < start:
                raise SkipItem(f"{bill_id} last action {date_matches[0]} ≤ cutoff")
        except ValueError:
            pass  # unparseable date — scrape this bill
    # No date found → fall through (scrape this bill — safe)
```

**Column index (`td[3]`):** Assumed to hold last-action text like
`"3/13/2026 S Died in Appropriations"` based on typical flsenate.gov table layout.
**Verify before committing:**

```python
from lxml import html; import urllib.request
tree = html.fromstring(urllib.request.urlopen(
    "https://flsenate.gov/Session/Bills/2026?chamber=both").read())
items = tree.xpath('//th/a[contains(@href, "/Session/Bill/")]')
print([td.text_content().strip()[:50] for td in items[0].xpath('../following-sibling::td')])
```

If the column index differs for special sessions, the empty-list fallback path handles
it safely — bills without a parseable date are always scraped.

**Performance impact:** Every bill that passes `BillList.process_item` triggers a
flhouse.gov `HouseSearchPage` request (60-second bot-detection backoff when blocked).
Skipping ~1,950 of ~2,000 bills eliminates ~1,950 flhouse.gov calls. FL scrape time
drops from 30+ hours to minutes on a nightly run.

Note: BillList still paginates all 38 pages to check dates — unavoidable without
server-side date filtering. But 38 lightweight HTML GETs are negligible.

---

### Part 4 — WA scraper

**File:** `openstates-scrapers/scrapers/wa/bills.py`

**How the scraper works today:**
- `scrape()` (line 241) → `scrape_chamber()` (line 259) → `GetLegislationByYear?year={y}`
  returns ~3,000 bill summaries (`LegislationInfo`) with NO date fields
- Then `scrape_bill()` (line 306) is called per bill → `GetLegislation?biennium=X&billNumber=Y`
  → response includes `CurrentStatus/ActionDate` (line 319)
- Each `scrape_bill()` also calls: `scrape_actions`, `scrape_sponsors`, `scrape_hearings`,
  `scrape_votes`, `scrape_chapter`, `scrape_cites` — 5-6 additional API calls per bill

**Approach — filter in `scrape_bill()` using `CurrentStatus/ActionDate`:**

`GetLegislationByYear` has no date filtering, so we still make one `GetLegislation` call
per bill. But after parsing that response we can check `CurrentStatus/ActionDate` and
skip the 5-6 downstream sub-scraper calls for unchanged bills:

```python
def scrape(self, chamber=None, session=None, start=None):
    # parse start= if provided (same format as other scrapers)
    self._start_dt = None
    if start:
        try:
            self._start_dt = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            self.warning(f"Invalid start= '{start}', doing full scrape")
    # ... rest of existing scrape() unchanged ...
```

In `scrape_bill()` (line 306), after fetching and parsing the `GetLegislation` response
(line 319), add an early-return check:

```python
# After: page = xpath(page, "//wa:Legislation")[0]
if self._start_dt:
    action_date_str = xpath(page, "string(wa:CurrentStatus/wa:ActionDate)")
    if action_date_str:
        try:
            action_dt = datetime.datetime.fromisoformat(action_date_str.rstrip("Z"))
            if action_dt <= self._start_dt:
                return  # skip sponsors, actions, hearings, votes, etc.
        except ValueError:
            pass  # unparseable — fall through to full scrape
```

**Impact:** One `GetLegislation` call per bill is unavoidable (no list-level date data).
But skipping the 5-6 downstream calls per unchanged bill reduces per-run API load by 5-6×
when most bills haven't changed. For WA's ~3,411 bills, if 50 changed: ~3,411 calls
instead of ~3,411 + 3,411×5 = ~20,466.

**Future upgrade path:** If `GetLegislativeStatusChangesByDateRange` exists in the WA
WSDL (verify at `http://wslwebservices.leg.wa.gov/legislationservice.asmx`), it would
return only bill IDs with status changes in a date range — eliminating the O(n)
`GetLegislation` calls entirely. Check the WSDL and upgrade the approach if available.

WA session ends each spring and is currently inactive; implement after FL/USA are validated.

---

### Part 5 — MI

**File:** `openstates-scrapers/scrapers/mi/bills.py`

**How the scraper works:**
- `scrape()` (line 47) → `POST https://legislature.mi.gov/Search/ExecuteSearch` with
  a search form body that includes `dateFrom=&dateTo=` parameters (currently empty, line 51)
- Returns HTML table; extracts bill links from `td[1]/a`
- `scrape_bill()` (line 78) → fetches per-bill detail page → `scrape_actions()` (line 111)
  reads History table where `td[1]` contains the action date

**Approach — populate `dateFrom=` in the search URL (fastest path):**

The search URL at line 51 already has `dateFrom=` in its query string. If this parameter
filters by last-action date (not just introduction date), adding `start=` support is a
near-zero-cost change:

```python
def scrape(self, session, start=None):
    date_from = ""
    if start:
        try:
            dt = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
            date_from = dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    # Pass date_from into the search URL/form body where dateFrom= currently appears
```

**⚠ Must verify:** The `dateFrom=` parameter's actual semantics — does it filter by
introduction date or last-action date? Test by setting `dateFrom=2026-06-01` and checking
whether bills with earlier last actions are excluded. If it only filters by introduction
date, this won't help for incremental runs (most bills were introduced months ago).

**Fallback if `dateFrom=` is introduction-only:** filter per-bill using the History table.
In `scrape_bill()`, the first row of `//div[@id='History']/table/tbody/tr` at line 115
has the most recent action in `td[1]`. Check this date and `return` early if ≤ start.
Still O(n) HTTP calls but avoids full bill processing.

**Note:** MI uses `--allow_duplicates` (pagination-overlap bug). This is unchanged.
MI does not use spatula — use `return` / `continue`, not `raise SkipItem`.

---

### Part 6 — UT

**File:** `openstates-scrapers/scrapers/ut/bills.py`

**How the scraper works:**
- `scrape()` (line 39) → `https://le.utah.gov/billlist.jsp?session={slug}` → HTML list
  with bill IDs and links only, **no date info in list**
- `scrape_bill()` (line 95) → for 2025+ sessions, calls `scrape_bill_details_from_api()`
  (line 214) → `GET https://le.utah.gov/data/{session}/{bill}.json` — **one request returns
  ALL bill data** including `actionHistoryList[0].actionDate` (most recent action)

**Approach — check `actionHistoryList[0].actionDate` after fetching JSON:**

Since the bill list has no date info, we must fetch each bill's JSON regardless. But once
we have the JSON, we can return early before processing sponsors, versions, actions, and
votes (all of which are in the same JSON blob — no additional HTTP requests, just parsing).

In `scrape_bill_details_from_api()` (line 214), after `data = json.loads(response.content)`
at line 218:

```python
if start and data.get("actionHistoryList"):
    most_recent = data["actionHistoryList"][0]  # list is newest-first
    date_str = most_recent.get("actionDate", "")
    try:
        # UT dates: "1/15/2026 1:41 PM" or "01/15/2026"
        action_dt = dateutil.parser.parse(date_str)
        start_dt = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M:%S")
        if action_dt.replace(tzinfo=None) <= start_dt:
            return  # skip sponsors, versions, actions, votes
    except (ValueError, TypeError):
        pass  # unparseable — fall through to full processing
```

**Impact:** UT makes exactly 1 HTTP request per bill (its JSON API is all-in-one). The
savings are processing time and DB import, not HTTP calls. UT sessions run Jan–Mar and
are currently inactive, so this is lower urgency.

**Note:** UT does not use spatula for this path — use `return` not `raise SkipItem`.
Pass `start` through the call chain: `scrape() → scrape_bill() → scrape_bill_details_from_api()`.

---

### Part 7 — MA

**File:** `openstates-scrapers/scrapers/ma/bills.py`

**How the scraper works:**
- `scrape_bill_list()` (line 87) → `GET https://malegislature.gov/api/GeneralCourts/{session}/Documents`
  → JSON array of all bills in the session (~10,891 records)
- Each record includes `PrimarySponsor.ResponseDate` and `Cosponsors[].ResponseDate`
  (ISO 8601 with ms, e.g. `"2023-01-04T10:02:36.727"`) — these are the dates sponsors
  **acknowledged** the bill, not the dates of legislative action
- `scrape_chamber()` (line 111) → iterates `self.bill_list` → `scrape_bill()` per bill

**Approach — filter in `scrape_bill_list()` using `PrimarySponsor.ResponseDate`:**

`ResponseDate` is a weak proxy — it reflects when a legislator last responded (e.g.,
added a cosponsor), not when the bill had floor action or a vote. For MA's 2-year sessions
with no vote events tracked, this may be the best available list-level signal.

In `scrape_bill_list()` at lines 95–109, before appending to `self.bill_list`:

```python
if start:
    start_dt = datetime.datetime.fromisoformat(start)
    # Collect all ResponseDates from primary sponsor and cosponsors
    response_dates = []
    if row.get("PrimarySponsor", {}).get("ResponseDate"):
        try:
            response_dates.append(
                datetime.datetime.fromisoformat(
                    row["PrimarySponsor"]["ResponseDate"].split(".")[0]))
        except ValueError:
            pass
    for cs in row.get("Cosponsors", []):
        if cs.get("ResponseDate"):
            try:
                response_dates.append(
                    datetime.datetime.fromisoformat(cs["ResponseDate"].split(".")[0]))
            except ValueError:
                pass
    if response_dates and max(response_dates) <= start_dt:
        continue  # skip this bill
```

**⚠ Caveat:** `ResponseDate` is sponsorship metadata. A bill with a new floor action
but no sponsor changes since `start` will be incorrectly skipped. For MA (which has
0 vote events — it doesn't scrape votes/actions), this may be acceptable. If MA ever
starts collecting votes, this filter would need to be revisited.

MA does not use spatula for bill list — use `continue`, not `raise SkipItem`.

---

### Part 8 — AZ

**File:** `openstates-scrapers/scrapers/az/bills.py`

**How the scraper works:**
- `scrape()` (lines 396–434) → POST to set session cookie → `GET https://www.azleg.gov/bills/`
  → HTML table of bill IDs with **no date fields**
- Per bill: `GET https://apps.azleg.gov/api/Bill/?billNumber=X&sessionId=Y&legislativeBody=Z`
  → JSON with full bill data including `BillStatusAction[].ReportDate` (ISO 8601 with ms),
  `IntroducedDate`, `PreFileDate`, `GovernorActionDate`

**Approach — check most recent `BillStatusAction.ReportDate` in the detail API response:**

Since the HTML list has no dates, we need the per-bill API call to get any date. This
means AZ incremental does NOT reduce HTTP calls — it reduces DB write and parsing work
per unchanged bill. The per-bill API call is unavoidable.

In `scrape_bill()` (or in the `scrape()` loop at line 432 after calling the detail API),
after loading the JSON:

```python
if start_dt and page:
    all_dates = []
    for action in page.get("BillStatusAction", []):
        d = action.get("ReportDate", "")
        if d:
            all_dates.append(d.split(".")[0])  # strip ms
    for key in ("IntroducedDate", "PreFileDate", "GovernorActionDate"):
        if page.get(key):
            all_dates.append(page[key].split(".")[0])
    if all_dates:
        latest = max(datetime.datetime.strptime(d, "%Y-%m-%dT%H:%M:%S")
                     for d in all_dates)
        if latest <= start_dt:
            continue  # skip sponsors, versions, votes sub-scraper calls
```

**Impact:** AZ makes 1 primary API call per bill already. Saving the follow-on sub-scraper
calls (sponsors, versions, votes — separate API calls) for unchanged bills is the main win.
AZ session runs Jan–April; currently inactive. Lower urgency.

AZ does not use spatula for bill list — use `continue` / `return`.

---

### Part 9 — VA

**File:** `openstates-scrapers/scrapers/va/bills.py`

**How the scraper works:**
- `scrape()` → `POST https://lis.virginia.gov/Legislation/api/getlegislationlistasync`
  with `{"SessionCode": <int>, "IncludeFailed": true}` → JSON with `Legislations[]` array
- Per bill: 4 additional API calls — events (`getlegislationeventbylegislationidasync`),
  texts (`getlegislationtextbyidasync`), patrons (`GetLegislationPatronsByIdAsync`),
  votes (`getvotebyidasync`)

**API research findings (2026-06-22):**

The bill list response has 5 date fields — `CandidateDate`, `VersionDate`,
`HousePassageDate`, `SenatePassageDate`, `IntroductionDate` — but **all are null for
every bill** across both the 2026 regular session (3,955 bills) and 2026S1 special
session (273 bills). These fields are never populated by the API.

Server-side date filtering does not exist:
- `startDate`/`ModifiedAfter`/`EventDateFrom` params in the POST body have no effect
  (still returns all 3,955 bills)
- Guessed date-range endpoints (`getlegislationbyeventdateasync`,
  `getlegislationeventbydateasync`, etc.) all return 404
- The `startDate` GET param on the per-bill events endpoint is silently ignored (returns
  the same full event list regardless)

The **only reliable date signal** is `EventDate` on individual event records returned by
`getlegislationeventbylegislationidasync`. Each event has a precise ISO 8601 timestamp.

**Approach — check max EventDate from the events call, skip remaining 3 calls if unchanged:**

The events call is already required for `add_actions()`. By checking `max(EventDate)`
before calling `add_versions()`, `add_sponsors()`, and `add_votes()`, we save 3 of 4
per-bill API calls for unchanged bills:

```python
def scrape(self, session=None, scrape_chunk_number=None, start=None):
    ...
    start_dt = None
    if start:
        try:
            start_dt = dateutil.parser.parse(start)
        except Exception:
            self.warning(f"Invalid start= '{start}', doing full scrape")
```

In the bill loop (line 92), refactor so events are fetched first and the result is
passed to `add_actions()` instead of re-fetched:

```python
for row in bill_list:
    ...
    bill = Bill(...)

    events_data = self._fetch_events(row["LegislationID"])
    self.add_actions(bill, events_data)   # pass pre-fetched data

    if start_dt:
        dates = [e["EventDate"] for e in events_data if e.get("EventDate")]
        if dates:
            latest = max(dateutil.parser.parse(d) for d in dates)
            if latest.replace(tzinfo=None) <= start_dt.replace(tzinfo=None):
                # Bill unchanged — skip texts, patrons, votes
                bill.add_source(...)
                yield bill
                continue

    self.add_versions(bill, row["LegislationID"])
    self.add_sponsors(bill, row["LegislationID"])
    yield from self.add_votes(bill, row["LegislationID"])
    ...
```

**Impact:** The bill list fetch (1 call) and one events call per bill are unavoidable.
But for unchanged bills, the 3 remaining per-bill calls (texts, patrons, votes) are
skipped. For the 2026 regular session with ~3,955 bills and ~50–100 changing per active
day: currently ~15,820 calls; incremental ~4,105 calls (~74% reduction). For a completed
session (most bills inactive), savings approach ~75%.

**Note:** VA sessions are short (Jan–Mar regular, occasional specials). The 2026 regular
session is complete; 2026S1 special session is the active one (273 bills). With only 273
bills and 4 calls each = ~1,092 calls per run, VA is the lowest-urgency jurisdiction for
incremental work — but the pattern is clean to implement.

`VA_API_KEY` must be set in the environment (from `.env` via `activate.sh`).

---

## Deployment convention

**Stale as of 2026-07-17 — kept for history, does not describe how `openstates-scrapers`
patches actually ship anymore.** This section originally described a local-patches/cherry-pick
mechanism (a throwaway branch, `cherry_pick <sha>` lines hand-added to `apply-local-patches.sh`).
`openstates-scrapers` became a formal DDP fork on 2026-07-17: fixes now merge via a normal
branch → PR → the fork's own `main`, and `apply-local-patches.sh` just does a plain
`git checkout main && git pull origin main` for it — no cherry-picking, no per-SHA list to
maintain. This is why the SHAs in the table above needed correcting: the original commits were
rewritten during that transition. See `PLAN-fork-management.md` §1 and `PLAN-open-states.md`
§2.5 for the current model. (`openstates-core` is different — it still uses a cherry-pick
mechanism, just range-based off a `cherry-pick-line` branch rather than hand-listed SHAs; not
relevant to this plan since none of the incremental-scraping work touches `openstates-core`.)

The `case "$STATE"` guard in `run-scrape.sh` can serve as a rollout gate — add each
state to the `case` as its scraper patch is validated.

---

## Files changed

| File | Change | Skip mechanism |
|---|---|---|
| `run-scrape.sh` | `--allow_duplicates` for FL; timestamp read/write; `$INCREMENTAL_FLAG` | — |
| `apply-local-patches.sh` | Cherry-pick SHAs for each state's `start=` patch | — |
| `scrapers/usa/bills.py` | Fix `%I`→`%M` + space→`T` at line 102 | existing (sitemap filter) |
| `scrapers/fl/bills.py` | `start=` in `scrape()` + filter in `BillList.process_item()` | `raise SkipItem` (spatula) |
| `scrapers/wa/bills.py` | `start=` in `scrape()`; early `return` in `scrape_bill()` after checking `CurrentStatus/ActionDate` | `return` (not spatula) |
| `scrapers/mi/bills.py` | `start=` in `scrape()`; populate `dateFrom=` in search URL OR early `return` in `scrape_bill()` | `continue` / `return` |
| `scrapers/ut/bills.py` | `start=` threaded to `scrape_bill_details_from_api()`; early `return` after JSON parse | `return` (not spatula) |
| `scrapers/ma/bills.py` | `start=` in `scrape()`; `continue` in `scrape_bill_list()` loop using `PrimarySponsor.ResponseDate` | `continue` (not spatula) |
| `scrapers/az/bills.py` | `start=` in `scrape()`; early `continue` in bill-rows loop using `BillStatusAction.ReportDate` | `continue` (not spatula) |
| `scrapers/va/bills.py` | `start=` in `scrape()`; refactor events fetch out of `add_actions()` to be called first; skip versions/patrons/votes if max `EventDate` ≤ start | `continue` (not spatula) |
| `RUNBOOK.md` | Document `logs/last-run/`, timestamp format, per-state rollout, VA API inspection step | — |

---

## Implementation order

Priority is by session activity and impact:

1. **Prerequisite** — `--allow_duplicates` for FL in `run-scrape.sh` (ship independently, now)
2. **Shell timestamp layer** — rest of `run-scrape.sh` changes
3. **USA** — 1-line fix, cherry-pick, validate (daily active, 10k bills, ~95% savings)
4. **FL** — verify `td[3]` column, cherry-pick, validate (daily active, 30-hr→minutes)
5. **WA** — `CurrentStatus/ActionDate` filter, cherry-pick, validate; also check WSDL for date-range endpoint upgrade
6. **MI** — verify `dateFrom=` semantics, cherry-pick, validate (weekly, 3,629 bills)
7. **UT** — `actionHistoryList[0].actionDate` filter, cherry-pick (weekly, session inactive)
8. **AZ** — `BillStatusAction.ReportDate` filter (weekly, session inactive, lower ROI)
9. **MA** — `ResponseDate` filter with caveat, or defer until better date signal found
10. **VA** — refactor events fetch; use max `EventDate` to skip 3/4 per-bill calls; low urgency (active session is only 273 bills)

---

## Verification

**Test 1 — timestamp mechanics:**
```bash
echo "2026-06-19T02:00:00" > logs/last-run/fl_session_2026.ts
bash -x ./run-scrape.sh fl "session=2026" 2>&1 | grep "start=\|Incremental"
# Expected: "Incremental run: start=2026-06-19T01:00:00"
```

**Test 2 — USA incremental (after cherry-pick):**
```bash
source activate.sh
$OS_UPDATE usa --scrape bills session=119 chamber=lower \
    start=2026-06-18T00:00:00 --cachedir $CACHE_DIR --datadir $SCRAPED_DATA_DIR
ls $SCRAPED_DATA_DIR/usa/bill*.json | wc -l
# Full ~4,000 files; 2-day window should yield <200
```

**Test 3 — FL incremental (after cherry-pick):**
```bash
source activate.sh
$OS_UPDATE fl --scrape bills session=2026 \
    start=$(python3 -c "import datetime; print((datetime.datetime.utcnow()-datetime.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S'))") \
    --cachedir $CACHE_DIR --datadir $SCRAPED_DATA_DIR 2>&1 | grep -c "SkipItem"
# Should see many SkipItem log lines and far fewer BillDetail fetches
```

**Test 4 — end-to-end cycle:**
```bash
rm -f logs/last-run/fl_session_2026.ts   # force full first run
./run-scrape.sh fl "session=2026"
cat logs/last-run/fl_session_2026.ts     # should show today's UTC timestamp
./run-scrape.sh fl "session=2026"        # second run uses timestamp
grep "Incremental run" logs/scraper.log | tail -5
```
