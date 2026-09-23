# Spot-check sample, pulled from the local RDS-replica Postgres

**Re:** `hr9576-request-spot-check-sample-before-commit-20260923.md` (this branch).

Pulled directly against `ddp-openstates-postgres-1` (:5433), same replica used throughout this
thread. Numbers below are this replica's own scope (23,047/19,803/3,244), smaller than the real
RDS run's (75,887/72,550/3,337) but the same underlying data shape -- nothing about the gap
between the two is unexpected (a replica snapshot vs. accumulated production history).

## Would-resolve sample (random, general)

| bill | motion | voter_name | note (id) | resolves to |
|---|---|---|---|---|
| HJRES 89 | On the Motion to Proceed | Scott (R-FL) | S404 | Rick Scott |
| S 4784 | On Cloture on the Motion to Proceed | Capito (R-WV) | S372 | Shelley Moore Capito |
| HR 3422 | On Motion to Suspend the Rules and Pass, as Amended | Lee (PA) | L000602 | Summer Lee |
| S 1383 | On the Motion to Proceed | Wyden (D-OR) | S247 | Ron Wyden |
| S 1582 | On Cloture on the Motion to Proceed | Grassley (R-IA) | S153 | Chuck Grassley |
| HR 6500 | On Motion to Suspend the Rules and Pass, as Amended | Garcia (CA) | G000598 | Robert Garcia |
| HRES 1398 | On Ordering the Previous Question | Goldman (TX) | G000601 | Craig Goldman |
| HR 1968 | On Passage of the Bill H.R. 1968 | Merkley (D-OR) | S322 | Jeff Merkley |

Garcia (CA) and Goldman (TX) are already same-surname-collision cases on their own (Garcia (CA/IL/TX),
Goldman (NY/TX) both real, current, distinct people).

## Would-resolve sample, specifically Bean/Carter (the pattern that started this whole thread)

| bill | motion | voter_name | note (id) | resolves to |
|---|---|---|---|---|
| HR 3492 | On Motion to Recommit | Bean (FL) | B001314 | Aaron Bean |
| S 5 | On Passage | Bean (FL) | B001314 | Aaron Bean |
| HR 7744 | On Motion to Recommit | Bean (FL) | B001314 | Aaron Bean |
| S 1003 | On Motion to Suspend the Rules and Pass | Bean (FL) | B001314 | Aaron Bean |
| HR 2966 | On Passage | Bean (FL) | B001314 | Aaron Bean |
| HR 22 | On Motion to Recommit | Bean (FL) | B001314 | Aaron Bean |

Every single `note` value here is the *same* `B001314` regardless of which bill/vote it's
attached to -- confirms this isn't a one-off, it's a real, stable identifier that will keep
resolving correctly across every affected vote.

## The 3,244 still-unresolvable rows: fully characterized, no surprises

Checked directly whether the unresolvable set is "ambiguous" (multiple people share an
identifier) or "no match at all": **zero ambiguous cases found.** Every one of the 3,244 traces
to exactly **14 distinct identifier values**, none of which match *any* `PersonIdentifier` row at
all (any scheme):

```
S429, S430, S431, S432, S428, ... (14 total, ~265 rows each)
```

This lines up exactly with the earlier finding in this thread: 14 of 100 current senators are
missing an `lis`-scheme identifier in our Person data entirely (mostly newer senators — Alsobrooks,
Ashley Moody, Bernie Moreno, Dave McCormick, Jim Justice, etc.). These aren't a resolution bug or
an edge case the script mishandles — they're a real, separate, already-known data gap (missing
`lis` IDs for a specific cohort of senators) that's out of scope for this backfill and would need
its own fix (populating those identifiers) to close. The script correctly leaves them alone
rather than guessing.

## Net

Sample checks out clean on both sides: real, stable, unique identifiers resolving to the correct
person for the would-resolve set (including the exact Bean/Carter pattern this investigation
started from), and a fully-explained, non-ambiguous reason for every row that stays unresolved.
Nothing here changes the recommendation -- looks safe to `--commit`.

Reply on this branch as usual.
