# Per-jurisdiction configuration: a full architecture survey (2026-08-22)

Backing detail for the `PRIMITIVES.md` → "Per-jurisdiction configuration: which mechanism to
use" entry. Written while scoping OPEN-120 (giving `ddp-broker-py`'s vote-matching code an exact
vote number instead of guessing from timing), which needed a new per-jurisdiction pattern inside
`openstates-core` and forced the question "where should that actually live?"

## The six mechanisms found, and where each one lives

| # | Mechanism | Repo | Shape | Example |
|---|---|---|---|---|
| 1 | A whole separate code folder per state | `openstates-scrapers` | `scrapers/<abbr>/`, a real Python package per jurisdiction (61 total) | `scrapers/mi/`, `scrapers/fl/` |
| 2 | A Python dict of settings objects | `openstates-core` | one dict, one entry per jurisdiction, holding real objects | `RESILIENCE_PROFILES` (`openstates/utils/resilience_profiles.py`) |
| 3 | A YAML settings file | `openstates-scrapers` | one top-level key per jurisdiction, categorized regex lists | `scrapers/config/motion_classification.yaml` |
| 4 | Bare inline conditionals in shared code | `openstates-core` | no registry at all — `if jurisdiction == "Virginia":` dropped directly into a shared function | `openstates/cli/text_extract.py` |
| 5 | A live database table | `ddp-broker-py` | one row per jurisdiction, editable without a deploy, with a `verified`/`verified_notes` audit trail | `JurisdictionEligibilityConfig` |
| 6 | Another YAML settings file, different repo | `ddp-sync` | per-jurisdiction (and per-flow) scheduling settings | `config/sync_schedule.yaml` |

Plus a smaller seventh case: plain hardcoded lists of state abbreviations sitting directly in
shell scripts (e.g. `run-scrape.sh`'s `--allow_duplicates` states, `mi fl va`) — not a named
mechanism, just a bash array someone added when a specific state needed a flag.

Nobody ever sat down and picked one convention for "per-jurisdiction configuration" across this
whole stack — each mechanism was a locally reasonable choice for the problem in front of whoever
built it, and never had to reconcile with the others.

## Why not force one mechanism across everything

The real dividing line isn't "scraper code vs. app code," it's **does this repo get merged from
a public project DDP doesn't control, or is it entirely DDP's own**:

- `openstates-core`/`openstates-scrapers` get merged from upstream regularly (`apply-local-patches.sh`,
  OPEN-98's cadence). Any DDP-only database table added there is a standing collision risk against
  whatever the public project adds on its own next — confirmed for real, not hypothetically, during
  OPEN-98's 2026-08-21 merge cycle: DDP's own `openstates/data/migrations/0046_billversiondocument.py`
  and upstream's new, unrelated `0046_bill_indexes.py` both descended from the same `0045` parent,
  requiring a real Django merge migration to reconcile. Every new DDP-only migration is one more
  thing that can collide with the next thing upstream adds.
- `ddp-broker-py` is entirely DDP's own app — nothing else changes its database out from under it.
  Its database-table convention (`JurisdictionEligibilityConfig`) is genuinely good: real
  `verified`/`verified_notes` audit trail, editable without a deploy. No reason to change it.
- `ddp-sync`'s YAML scheduling config is a different domain (timing, not text/vote parsing) and
  wasn't touched by this survey.

**Decision**: within `openstates-core`/`openstates-scrapers` specifically, standardize on
mechanisms 2 and 3 above (Python dict / YAML file) — both proven, neither carries upstream-merge
risk. Phase out mechanism 4 (bare inline conditionals) opportunistically. Don't try to unify
`openstates-core` and `ddp-broker-py` onto the same mechanism — that would mean either giving the
scraper a live runtime dependency on the broker app while it scrapes, or putting a database table
into a repo that gets merged from a public project. Both cost more than "one store for everything"
is worth.

## How much of this is even DDP's own code, vs. inherited from the public project

Checked directly (author-based, full history, not just "since the last upstream merge" — that
window keeps resetting every time DDP merges upstream, which would otherwise undercount):

**The base per-state code (`openstates-scrapers/scrapers/<abbr>/`) is almost entirely upstream.**
Across DDP's 8 tracked jurisdictions, DDP has made 71 commits out of 773 total — about 9%:

| Jurisdiction | DDP commits | Total commits | DDP share |
|---|---|---|---|
| Michigan | 18 | 76 | 24% (DDP's heaviest state — matches the WAF-blocking history) |
| Massachusetts | 9 | 84 | 11% |
| Utah | 8 | 82 | 10% |
| Washington | 6 | 62 | 10% |
| Florida | 11 | 137 | 8% |
| Arizona | 6 | 80 | 8% |
| Virginia | 9 | 144 | 6% |
| US Congress | 4 | 108 | 4% |

**The newer, structural per-jurisdiction mechanisms are the opposite — 100% DDP, brand-new files
that don't exist upstream at all**: `resilience_profiles.py`, `version_ordering.py`, `mi_cookies.py`,
`fl_cookies.py`, `cookie_provider.py` (all confirmed via `git show origin/main:<path>` failing --
the file simply isn't there).

**`text_extract.py` is the one genuinely mixed file**: of 44 commits total, 26 are DDP's
(Ramon Perez, Agent Smith), 18 are upstream's (John Seekins, James Turk, Jesse Mortenson — known
public-project maintainers). The two jurisdiction-specific bits already there before DDP touched
it (Florida's TLS-cipher fix, a California jurisdiction-ID check) are inherited byte-for-byte
unchanged; everything else jurisdiction-specific in that file is DDP's own addition.

**Overall shape**: the foundation (one folder per state, the basic scrape logic) is almost
entirely the public project's work that DDP rides on top of. Every one of the newer, more
structured per-jurisdiction mechanisms worth having an opinion about architecturally is something
DDP built from nothing, specifically because DDP hit a problem the public project's own code
didn't already solve.

## What came out of this survey

- **OPEN-121** — consolidate `text_extract.py`'s WA/MI/VA/AZ inline jurisdiction checks into a
  dict-based cleaner registry (mechanism 4 → mechanism 2), explicitly excluding the two
  upstream-inherited FL/CA checks and `version_ordering.py` (not actually jurisdiction-keyed).
- **OPEN-120** — corrected to design its new vote-number extraction pattern as a mechanism-2-or-3
  style registry living inside `openstates-core` itself, not a reuse of `ddp-broker-py`'s
  `JurisdictionEligibilityConfig` (a real conflation caught during review — that model lives in a
  different repo the scraper has no access to). Also gained a full per-jurisdiction viability
  check: of DDP's 8 tracked jurisdictions, only US Congress currently has both a real per-vote
  number in its activity log *and* a matching number already stored on the vote record itself;
  Michigan has the first but not the second (a real gap, second piece of work needed); Massachusetts
  has the first but isn't tracked by `ddp-broker-py` at all yet; FL/WA/VA/UT/AZ don't have a
  usable per-vote number in their real text at all.
- **`jurisdiction-config`** Jira label — applied to the tickets that are actually about this theme
  (OPEN-120, OPEN-121, OPEN-58/59/60/61/62/64, BROKER-47, BROKER-107), not to unrelated tickets
  that merely came up in the same conversation.
