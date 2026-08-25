# OPEN-158 — how often can MI's last-action diff miss a real change?

**2026-08-25. Answer: 1.20% of bills are genuinely at risk, and what gets missed is substantive —
adopted substitutes, committee reports, floor referrals. This is NOT negligible, and the backstop
the design assumes does not exist. It needs a decision; a recommendation is at the bottom.**

Zero network requests. Answered from the production replica plus one already-cached search page,
per the method OPEN-89, OPEN-134 and OPEN-150 each used — MI is the fleet's most WAF-sensitive
jurisdiction (OPEN-52/53/54) and that record is worth keeping.

## Correction: my first measurement was wrong, and the error mattered

The first pass counted only **adjacent** duplicate actions and found 4 bills (0.102%), concluding
"effectively zero, accept and change nothing." A `/pm-review` round rejected that, correctly.

The scraper compares the **previous run's** stored last-action text against the **current run's**.
So a miss happens whenever the same normalized text is the last action at two different observation
points with actions added in between — which includes **non-adjacent** repeats. Previous run sees
`A` as last; by the next run the bill has gained `B` then `A` again; the visible string is unchanged
and the bill is skipped, losing `B`. Adjacent duplicates are only the special case where exactly one
action is lost.

I also wrote that the feared repeated committee referral "does not occur anywhere in the corpus."
**That was flatly wrong.** `referred to Committee on Appropriations` is the single most common
repeated string, 49 occurrences.

## The corrected measurement

Condition: for each bill, any pair of positions *p* < *k* (ordered by the `order` column) where
`_mi_normalize_last_action()` of both descriptions is equal.

| | pairs | bills | share |
| --- | --- | --- | --- |
| Adjacent only (the wrong first pass) | 4 | 4 | 0.102% |
| **Non-adjacent** | **379** | **278** | **7.085%** |
| Any repeat | 383 | 280 | 7.136% |

A repeat is only *reachable* as a miss if every action between the two occurrences falls inside one
inter-scrape interval — otherwise a run lands among them, sees a different last action, and pulls the
bill. MI runs weekly, so the necessary condition is a span of ≤ 7 days:

| Scrape cadence | Window | At-risk pairs | At-risk bills | Share |
| --- | --- | --- | --- | --- |
| nightly | ≤ 1d | 31 | 21 | 0.54% |
| **weekly (today)** | **≤ 7d** | **63** | **47** | **1.20%** |
| fortnightly | ≤ 14d | 106 | 70 | 1.78% |

Nightly would roughly halve the exposure but is not available: MI is WAF-capped at 10 rpm and is
explicitly excluded from OPEN-140's cadence escalation for that reason (OPEN-53).

## What actually gets missed — this is why 1.20% is not acceptable on its own

Not cosmetic rows. Real examples from the at-risk set:

```
SB 303    repeat 'referred to Committee on Health Policy'  (7d span)
          missed -> REPORTED FAVORABLY WITHOUT AMENDMENT 5/20/2025
          missed -> REFERRED TO COMMITTEE OF THE WHOLE
          missed -> RULES SUSPENDED FOR IMMEDIATE CONSIDERATION

HB 4420   repeat 'LAID OVER ONE DAY UNDER THE RULES'       (6d span)
          missed -> substitute (H-3) adopted
          missed -> Senate substitute (S-4) concurred in as substituted (H-3)
```

A committee report, a floor referral, and two adopted substitutes. The distribution of how much
would be lost per occurrence: 7 pairs lose 1 action, 10 lose 4, 6 lose 10, 5 lose 11, and **one
pair loses 25 actions.** Four pairs lose 0 (the repeat is immediately consecutive).

## The mitigation I first proposed is impossible

The first version of this note suggested including the bill's **action count** in the diff key,
"because the count comes off the same search row already being parsed." **That was an unverified
assumption and it is false.** Checked against a real cached search page — all 3,924 rows,
`legislature.mi.gov,Search,ExecuteSearch,...` — `td[3]` contains the bill's title/summary followed
by `Last Action: <text>` and nothing else:

```
td[1]: SB 0001 of 2025
td[2]: Senate Bill
td[3]: Civil rights: public records; ... Amends sec. 2 of 1976 PA 442 (MCL 15.232). TIE BAR WITH: SB 0002'25
td[3]: A resolution notifying the Governor ... session.Last Action: ADOPTED
```

No action count, no date, no sequence number — which is exactly what OPEN-150 said, and I should
have believed it. **The last-action string is the only per-bill signal the search page carries.**
So no cleverer diff key is available without fetching bills, and fetching bills is the cost the
whole design exists to avoid.

## The backstop this design relies on does not exist

OPEN-150's note closes its false-negative bullet with *"The periodic full scrape is the backstop."*
There is no periodic full scrape.

`run-scrape.sh` does a full walk only when `logs/last-run/<key>.ts` is absent. `mi.ts` exists
(written 2026-08-24) and **nothing in this repo ever removes a `.ts` marker** — grepped across every
shell script. Nor is any full/forced MI walk configured in ddp-sync's `sync_schedule.yaml`. So MI has
had exactly one full walk, when the marker was first absent, and will never have another.

This is the same shape as OPEN-86's finding, where the `do_scrape()` wipe deferral rested on a
recovery import gated behind a flag nothing set: **a safety claim resting on a mechanism that was
never built.** Worth naming as a pattern, since it is now twice in one plan.

## Recommendation

**A monthly full walk, implemented as clearing MI's `.ts` marker on a schedule.** Rationale:

- It needs **no new logic**. `run-scrape.sh` already does a full walk when the marker is absent, so
  this is a scheduling change plus a marker delete — not a new diff mechanism to design and test.
- It bounds staleness to one month rather than to the session, which is the actual guarantee the
  design was documented as already having.
- Cost is 3,924 fetches at 10 rpm ≈ **6.5 hours, once a month.** That is affordable on a
  jurisdiction whose incremental runs are weekly and cheap.

Costed but **not** recommended: a targeted re-fetch of only bills whose current last action is one
of the 27 repeat-prone strings. That is 1,134 bills (28.9%) ≈ **113 minutes** — 3.5x cheaper than a
full walk, but it needs new logic to maintain the repeat-prone set and would run against a moving
target. Not worth the machinery for something that runs monthly. Recorded so it need not be
rediscovered if the full walk ever proves too expensive.

Explicitly rejected: nightly scraping (WAF, OPEN-53) and any richer diff key (no signal exists).

## What this closes and does not close

- **Closes** OPEN-150's "What was NOT examined" item on false negatives — with the opposite answer
  from the one my first pass gave. The hole is real, bounded, and now quantified.
- **Supersedes** OPEN-134's evidence bar 2 ("the ~80/week figure measurably drops"), which is a
  tautology: with the date filter gone every bill appears on the sweep, so the count of
  *unreturnable* bills is structurally zero. The 1.20% figure is what characterises residual risk.
- **Does not** claim the 1.20% is currently causing loss. It is the reachable rate, not an observed
  one — establishing that would need run timestamps correlated against action dates, and MI's
  per-run history does not go back far enough to do it for a two-year session. Stated as a limit,
  not glossed.
- **Does not** cover under-collection generally. A bill whose last action is *stale on MI's own
  search page* is a different failure and is not measured here.
- **Re-measure if** the session rolls over (a fresh session's history is short and early figures
  will be noisy), or if `_mi_normalize_last_action()` becomes more aggressive than
  whitespace-and-case — anything cleverer raises the collision rate by construction, which is why
  that function's docstring says to stay literal.

## Reproducing

Read-only, zero network.

```python
norm = lambda t: re.sub(r"\s+", " ", (t or "")).strip().lower()   # exactly as mi/bills.py does
# per bill, ordered by opencivicdata_billaction."order", record the first index of each normalized
# description; on a repeat at index k with first occurrence p, the pair is reachable as a miss iff
# (date[k] - date[p]).days <= <scrape interval in days>
```
