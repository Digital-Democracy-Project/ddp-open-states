# OPEN-86 — the sweep-import canary, finally run

**2026-08-25. The sweep works. Both shipped constants are right for a small jurisdiction. But the
sweep re-stages the entire accumulated data directory every cycle, which makes it unsafe to widen to
MI, FL, MA or USA — the exact jurisdictions this ticket named as its next step — and the failure mode
is a successful multi-hour scrape failing at the final import.**

Run against Arizona in an isolated environment: separate database (`openstates_dev`, 2,065 bills, not
production's 73,250), separate data and cache directories. AZ rather than VA because it is the
jurisdiction SYNC-35 actually cost 895 bills — this ticket's own motivating incident — and unlike VA
it currently has bills to scrape.

## Why VA could never close this

Five consecutive VA runs scraped `bills_scraped=0`; VA is out of session. With no files there is
nothing for a cycle to stage or import.

There is a second reason that matters more, because it means waiting for another Saturday was never
going to work: **a no-op VA run exits in about 90 seconds, and the first sweep tick is at 120
seconds.** VA's runs end before the loop's first `sleep` returns. The mechanism was never reached,
not merely starved of data.

## The observability bug — a successful cycle logged nothing

The success branch of the sweep loop was a bare `SWEEP_FAILURES=0`. Only `rc=2` (lock busy) and
`rc!=0` (failure) logged anything at all.

Two consequences, and the second is the one that cost time:

1. **Criterion 3 was unmeasurable.** "Measure the real `SWEEP_INTERVAL`/`LOCK_WAIT` values from a
   run" had nothing in the log to measure.
2. **`grep sweep logs/scraper.log` returning empty was read as proof the loop had never executed a
   cycle.** That grep cannot detect a *working* cycle either, so it was never evidence. Confirmed
   directly on this canary: nine successful cycles ran and produced **zero** matches for it. The
   conclusion happened to be true for VA, for the 90s/120s reason above, but the reasoning did not
   hold and would have been wrong for any jurisdiction that actually scrapes.

Fixed by logging one line on the success path — cycle number, files staged, elapsed seconds against
the configured interval. Verified live:

```
Sweep cycle 1 imported for az: staged=15 files, took 1s (interval 45s)
Sweep cycle 2 imported for az: staged=31 files, took 2s (interval 45s)
Sweep cycle 3 imported for az: staged=45 files, took 2s (interval 45s)
```

## Criterion 3 — measured

Ten cycles, 426 bills, **zero lock contention, zero skipped cycles, zero failures.**

| cycle | start | gap | staged | import result |
| --- | --- | --- | --- | --- |
| 1 | 11:21:11 | — | 16 | `11 new 1 updated 4 noop` |
| 2 | 11:23:13 | 122s | 38 | `22 new 0 updated 16 noop` |
| 3 | 11:25:17 | 124s | 63 | `25 new 0 updated 38 noop` |
| 5 | 11:29:28 | 126s | 101 | `21 new 0 updated 80 noop` |
| 7 | 11:33:43 | 127s | 134 | `18 new 0 updated 116 noop` |
| 9 | 11:38:05 | 131s | 177 | `20 new 0 updated 157 noop` |

The `sleep` is a fixed 120s, so `gap − 120` is the import duration: 2s at 38 staged files rising to
11s at 177. That is **~62 ms per staged bill, linear.**

**Both constants are correct as shipped for a jurisdiction this size, and neither is changed.**
`SWEEP_INTERVAL_SECS=120` is generous — the import finishes in a small fraction of it — and
`LOCK_WAIT_TIMEOUT_SECS=180` was never approached.

Scope that claim honestly: this validates the constants **for AZ, at up to 177 staged files, against
an isolated dev database**. It does not establish them for a larger jurisdiction, for production data
volume, or under contention, none of which this canary exercised.

## Criterion 4 — the rollout, and the finding that blocks it

**Every cycle re-stages the whole accumulated data directory, not just new files.** Visible above as
the `noop` column climbing 4 → 16 → 38 → 63 → 80 → 101 → 116 → 134 → 157: each cycle re-imports
everything already imported. So import cost grows all run long and the last cycles dominate.

At ~62 ms per staged bill the final cycle would cost roughly:

| jurisdiction | bills/run | final-cycle import |
| --- | --- | --- |
| AZ (this canary) | 895 | ~56s |
| UT | 1,021 | ~63s |
| MI | 3,924 | ~244s |
| FL | 7,685 | ~478s |
| MA | 11,592 | ~720s |

Treat those as **provisional guardrails, not a precise limit.** They extrapolate a linear fit
measured only to 177 staged files, on a dev database, out to 60x that. The direction is solid; the
exact numbers are not load-bearing, and the bill counts are recent observations rather than
session-peak figures.

### The failure mode, stated correctly

An earlier draft of this note said cycles would "pile up" and trip the 3-consecutive-failures
escalation. **Both halves of that were wrong**, and the real mechanism is worse:

- The sweep uses `try_import_lock`, which is **non-blocking** — a busy lock returns 2 and the cycle
  is skipped with a log line. Cycles are a single sequential loop and cannot overlap. A skipped cycle
  does **not** increment `SWEEP_FAILURES`, so no escalation fires.
- The recovery and **final** imports use `require_import_lock`, which **blocks up to
  `LOCK_WAIT_TIMEOUT_SECS` and then fails loudly** — returning nonzero into `set -e` and the `ERR`
  trap.

So the actual risk is: **the scrape finishes while a late sweep cycle's import is mid-flight, the
final import waits 180s, times out, and the entire run fails.** For MA that in-flight import is
projected at ~720s, four times the wait. A successful eight-hour scrape would end in a failed run —
which is precisely the "a failure that reports success" family inverted into "a success that reports
failure", and it destroys the run's completeness guarantee rather than merely alarming someone.

### Decision

- **Blocked for MI, FL, MA and USA** until the staging behaviour is fixed. Not a tuning question:
  raising `LOCK_WAIT_TIMEOUT_SECS` past a 720s import would mean a final import that stalls for
  twelve minutes, and lowering `SWEEP_INTERVAL_SECS` makes it worse.
- **AZ and UT are plausible next candidates** but should not be enabled on this evidence alone. What
  is missing is one full run to completion at final-cycle size, so the projected ~56s/~63s is
  measured rather than extrapolated.
- **`sweep_import.jurisdictions` is unchanged by this work — still `["va"]`.** Widening it is a
  config edit and an operator decision, not something this note does.

## The staging fix belongs to its own ticket

The root cause is one behaviour: stage only files not yet imported, rather than the whole directory
each cycle. That changes *what the sweep imports* and needs its own design — how to track what has
been imported across a run, and what happens to the excluded-file list the failure path maintains.
Deliberately not folded in here. **It is the blocker for the MI/FL/MA/USA rollout and should be filed
as such**, so that dependency does not become tribal knowledge.

## A retraction

OPEN-154's description claimed this ticket's measurement work "found real imports up to 345s against
a 180s lock-wait timeout." **I wrote that, it was never measured, and it is removed.** The number was
invented.

The phenomenon it gestured at turns out to be real for large jurisdictions — MI ~244s, FL ~478s, MA
~720s all exceed the 180s wait. That does not retroactively justify having asserted it. The right
sequence was to measure first, which is what this note does.

## What remains open

- The staging fix, and the MI/FL/MA/USA rollout that depends on it.
- One full-run measurement on AZ or UT before widening to them.
- Behaviour under real contention, which this canary did not exercise — zero cycles were skipped.
- Whether production data volume changes the 62 ms figure materially.
