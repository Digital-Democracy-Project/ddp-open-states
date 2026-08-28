# OPEN-181 — externalising per-source scraper memory (2026-08-27)

Phase 0 of `PLAN-scraper-execution-migration.md`, closing `PLAN-scraper-execution-contract.md`
§4 — the one clause of six recorded as **"does not conform"**, and the one §7 calls "the big
one". A scrape can only run somewhere disposable if it can find out what it already collected
without reading this machine's disk.

## What memory actually was, measured rather than assumed

| Kind | Where | Size | Migrated? |
|---|---|---|---|
| Watermarks (`.ts`, `.count`, `.imported`) | `logs/last-run/` | **56 files** | **Yes** |
| Michigan's last-action baseline | `_cache/mi_last_actions_2025-2026.json` | 202 KB, 3,924 entries | **Yes** |
| scrapelib HTTP cache | `openstates-scrapers/_cache/` | 2.8 GB, ~105k entries | **No — see below** |

**`logs/last-run/` holds 333 files, and only 56 of them are memory.** Worth stating because the
difference is not obvious and an earlier draft of this note quoted the 333: **270 are `*.done`
files belonging to the staleness watchdog** (`check-scrape-staleness.sh`), which are
alert-suppression state on the monitoring side and have no bearing on what a scrape collects; one
more is its `.schedule-unreadable-alerted` sentinel; 4 are `.bak-*` copies of deliberately
superseded watermarks; and 2 are `--help.ts`/`--help.count`, junk left by an old mis-invocation.
The migration script reports `uploaded=57` — the 56 markers plus Michigan's baseline — and
`skipped=2`, the `--help` pair. The `.bak-*` files never enter the loop, because a name ending
`.ts.bak-pre-waf-rescrape-20260730` does not match the `*.ts` glob.

## The store: S3, through the wrapper that already exists

Not much of a contest. `ddp-prod-s3-openstates-backups` is already a readable `STANDARD_IA`
bucket with `put`/`get`/`ls`/`info` and its own scoped IAM user, and it is **the only cloud store
reachable from this machine at all** — `~/.aws` is root-owned with no readable credentials, and
that wrapper's single sudo entry is allowlisted while general sudo is not.

The obvious alternative, the openstates Postgres, is wrong by construction: it is *on* the
machine the scrapes are being moved off, and it does not move until Phase 2 — after collection
has already gone in Phase 1.

## Three decisions that are not obvious

**1. "The store did not answer" is not "the store is empty."** `scraper_memory_fetch` returns
three values, not two: fetched, genuinely-absent, and could-not-tell. §4 says absent memory means
a full collection — and for Michigan it means refusing to run at all — so collapsing a transient
S3 failure into "absent" would convert a network blip into a ~3,900-request full walk of the
fleet's most block-sensitive site. That is precisely the self-inflicted outage §4 warns about.
Absence is therefore matched **positively**, on the 404 the wrapper returns for a missing key
(verified live: `get` on a missing key exits 1 with `An error occurred (404) ... Not Found` and
writes no destination file; `ls` on an empty prefix exits non-zero with no output). Everything
else fails the run, writes no markers, and leaves the window eligible.

**2. The namespace has no default and a run refuses without one.** OPEN-159 and OPEN-172 were
both incidents where a dev checkout silently read and then *wrote* production's watermark files,
because a path defaulted to production. An object key has no checkout to follow, so the same
mistake in a shared bucket would be a dev run overwriting production's memory with no local
filesystem clue that it happened. `SCRAPER_MEMORY_PREFIX` is required.

**3. Michigan's baseline is found by name, not built from a template.** This was caught by
dry-running the migration against production's real inventory rather than by reasoning:
**production runs Michigan with no session argument** — its markers are a bare `mi.ts` — so the
session inside `mi_last_actions_<session>.json` is the *scraper's* notion of the current session,
derived in `mi/bills.py`, not anything the wrapper was told. A filename template produced
`mi_last_actions_.json` and matched nothing. So the config is a glob, the store is asked what it
holds, and the file names itself.

Related: the sync lives in the **runner**, not in the scraper. The contract puts memory on the
runner's side of the line, and `openstates-scrapers` is a fork of a public project DDP does not
control — an S3 client inside `mi/bills.py` would be a permanent merge conflict against every
future upstream pull. `mi/bills.py` is untouched and still reads the same path it always has.

## The HTTP cache: not migrated, and what that costs

Decided explicitly, because the ticket is right that silence here is the failure mode.

**It is not memory.** Nothing about correctness depends on it — a run without it collects the
same bills, and §4's semantics are carried entirely by the watermarks and Michigan's baseline.
It only makes `--fastmode` possible. It is also a cache of other people's web pages, rebuilt
continuously, so a copy would be stale on arrival. Cost was not the deciding factor and is small
either way: 2.8 GB at `STANDARD_IA` is roughly **$0.04/month** plus about a dollar of one-time
upload.

**What not migrating costs, stated so the first cloud run is not a mystery:** a disposable runner
starts with an empty cache, so `--fastmode` — the automatic second attempt `run-scrape.sh` makes
after a failed scrape — has nothing to read and will not rescue a failed run the way it does
here. The first run on any new runner fetches everything from the source site. That matters most
for Michigan: ~3,900 fetches against a hard 10 requests/minute cap, so roughly 6.5 hours. A
throughput cost on cutover, not a correctness one.

## Ordering, which is the only safety this store can offer

The wrapper exposes `put` / `get` / `ls` / `info` and nothing else — no transaction, no
conditional put, no delete. So several objects cannot be published together, and a failure part
way through cannot be rolled back. What *can* be arranged is which object becomes visible last,
and that turns every partial failure from dangerous into merely wasteful:

1. **Michigan's baseline is published first.** It is what makes an incremental run *safe*.
2. **`.count` and `.imported` next.** Reporting only; nothing reads them to decide what to collect.
3. **`.ts` last.** It is what *authorises* an incremental run, and an incremental run skips
   everything before its cutoff.

Persistence stops at the first failure. So the combination to avoid — a fresh cutoff sitting
beside a stale baseline, which would make Michigan run incrementally against stale actions and
silently skip bills that had moved — is unreachable. Any failure leaves the watermark where it
was and the next run re-collects a window that was already collected.

**The claim is precise: publication is ordered, not atomic.** Every failure mode it leaves behind
is one where a window gets re-collected, never one where a window gets skipped.

### The invariant that makes cache-first safe, which is not obvious

Publishing the baseline *first* looks alarming on its own: Michigan builds its fetch set by
comparing the site against the baseline (`mi/bills.py`: `if bill_no_key not in changed_nos:
continue`), so a bill already recorded there is not re-fetched. A fresh baseline beside a stale
cutoff would seem to hide bills that moved.

It does not, and the reason is worth writing down because nothing said it before: **both persist
calls sit on the success path, after the import's exit status has been checked.** A failed scrape
and a failed import each exit earlier and publish nothing at all — not the baseline, not the
markers. Michigan's own code lines up with that: `scraped_actions[bill_no]` is assigned only
after `yield from self.scrape_bill(...)`, and the saved baseline is `baseline + scraped_actions`,
so on an incremental run it advances only for bills the run actually fetched.

**Stated no more strongly than that, deliberately.** On a *full* run MI replaces the baseline with
the whole page (`merged = dict(site_actions)`) — its own pre-existing OPEN-134 design, not changed
or relied on here — and a zero exit from the importer is the importer's own report rather than an
independent durability proof. The claim this ordering needs is only: *the run's scrape and import
both reported success before anything was published.*

The stale watermark then costs a re-collected window rather than a skipped one. For Michigan that
costs little, since its skip decision is baseline-driven rather than cutoff-driven — but "little"
is not "nothing" for a jurisdiction that does filter on the cutoff, and the honest general
statement is duplicated work, not free.

All three boundaries are asserted rather than argued: a run whose import fails publishes nothing
even with a fresh baseline in its cache directory; a cache-publication failure blocks every marker
write (fail-closed, not merely ordered — verified by removing the guard and watching the test
fail); and a watermark failure after a successful cache publication leaves the new baseline beside
the *previous* cutoff, which is the safe pairing. The store snapshots compare file **contents**,
because a path listing is unchanged when an object is overwritten in place.

## Validation — live, against the real bucket

Two real Utah scrapes from the dev checkout against the isolated `openstates_dev` database, with
`SCRAPER_MEMORY_BACKEND=s3` and prefix `scraper-memory/dev-open181`.

| Case | What ran | Result |
|---|---|---|
| **Memory absent** | no local markers, empty store | `mode=full`, `status=ok`, 5 bills; the three markers appear in the bucket |
| **Memory present, and this machine knows nothing** | **local markers deleted**, only the S3 objects survive | `mode=incremental cutoff=2026-08-28T01:59:11`, `prev_run=5 (full)` — both read back from the store |
| **`unparsed` advances memory** | that second run's import printed no countable line | exit `0`, stored watermark advanced `02:59:11` → `03:01:09`, stored marker became `unparsed::::incremental` |
| **Michigan's baseline round-trips** | the real 202 KB / 3,924-entry file, put and fetched back through the real bucket | **byte-identical**, `md5 d9e0d0e8cfc59bbbadc407c780fbef0f` both ways |
| **MI still refuses without a baseline** | `mi/bills.py`'s OPEN-134 guard, untouched | its own 28 tests pass |

`unreachable` **not** advancing the stored memory is asserted through the real script with a stub
scraper rather than live, for the same reason `test-no-op-side-effects.sh` does it that way: the
live path forces `SUPPRESS_FAILURE_ALERT=0` on purpose, so provoking a genuine block would fire
real Slack and CAMS traffic.

**Production was not touched by any of it.** Its `ut` markers, and every marker other than the
two named below, are byte-identical across the whole exercise — these runs only ever wrote
`ut_session_2025S2` in the *dev* checkout, which is a different key in a different directory.
The two that did change are `usa_session_119_chamber_lower` and `_upper`, which production
advanced on its own schedule while this work was going on; the Washington scrape that was running
in production throughout ran to completion undisturbed. Worth stating precisely rather than
claiming a clean checksum, because "nothing changed" and "nothing *I* changed" are different
claims and only the second one is true here.

## Honest caveats

- **"Without touching this machine's local filesystem" needs one qualification.** The wrapper's
  interface is file-based (`put <local-file>`, `get <key> <local-file>`), so a run still stages
  its memory through local files. What changed is which copy is *authoritative*: the store is,
  and the local files are a per-run cache of it. The demonstration is that deleting them changed
  nothing. On a disposable runner that directory is ephemeral by construction.
- **An empty store does not erase a local marker.** That is what makes the cutover seamless — no
  jurisdiction gets a gratuitous full collection on the day the switch is flipped. The cost is
  that deleting an object does not by itself force a full collection *on this machine*; forcing
  one means removing both copies.
- **The wrapper has no delete command**, so the handful of `scraper-memory/dev-open181/…` test
  objects (a few hundred KB) remain in the bucket.
- **Piping this script's stdout into a truncating consumer kills the run.** Hit while validating:
  `run-scrape.sh ... | head -2` closed the pipe and `log()`'s `tee` took SIGPIPE mid-import. Not
  new and not changed here, but worth knowing given the contract describes reading the last line
  of stdout — a consumer must drain the whole stream.

## Not switched on

`SCRAPER_MEMORY_BACKEND` defaults to `local`, which makes every function a no-op. The nightly
scrapes are unaffected until someone sets it, which is the ticket's rollback criterion: a failed
cutover is a config change back, not a revert.
