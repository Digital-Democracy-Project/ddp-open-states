# Why VoteBot's vote-party breakdown buckets ~1 in 4 US Congress votes as "Unknown/Other" (2026-07-26)

## The bug (OPEN-2)

VoteBot's "Status & votes" button shows a party breakdown for a bill's roll-call votes. For
almost every US Congress bill, a large chunk of legislators show up under "Unknown/Other"
instead of Democratic/Republican. Reported example: HR 8646 (Agriculture appropriations,
2026-06-04 final passage) showed 51 Yes / 42 No / 2 Other as "Unknown/Other" out of 430 total
votes.

## Confirmed in both places named in the ticket

- **Public API** (`v3.openstates.org/bills/us/119/HR8646?include=votes`, real key from
  `ddp-broker-py/.env`): the "On Passage" vote has 430 individual vote records, of which
  **95 have `voter: null`** — no linked person, no party. Breakdown: 51 yes / 42 no / 2 not-voting.
  Exact match to the ticket's numbers.
- **Local Postgres fork** (`openstates` DB, `:5433`, queried read-only): `opencivicdata_personvote`
  has the identical 95/430 rows with `voter_id IS NULL`, same 51/42/2 breakdown. Our fork isn't
  diverging from upstream here — it inherited the same gap.

## Root cause: Congress.gov's data is fine; our importer never uses the identifier it already has

Every "null" voter name traces to a legislator who shares a surname with another sitting member
(three different Garcias, three different Carters, etc. in a 435-member House). The House
Clerk's roll-call XML (`clerk.house.gov/evs/2026/roll205.xml`, free, no key needed — the same
source our own scraper already uses) already disambiguates these:

```xml
<recorded-vote>
  <legislator name-id="G000598" sort-field="Garcia (CA)" unaccented-name="Garcia (CA)"
              party="D" state="CA" role="legislator">Garcia (CA)</legislator>
  <vote>Nay</vote>
</recorded-vote>
```

`name-id` is a stable bioguide ID. It resolves cleanly and uniquely in our own DB:
`G000598` → Robert Garcia, `G000586` → Chuy García, `G000587` → Sylvia Garcia — three distinct
people already present in `opencivicdata_personidentifier` (scheme `bioguide`).

The gap is entirely in DDP's/OpenStates' own pipeline, not the source data:

- `openstates-scrapers/scrapers/usa/votes.py` already extracts this bioguide (House, `:212`)
  and the equivalent `lis_member_id` (Senate, `:315`) — but only ever passed it through as an
  inert `note=` string. A `# TODO: bioguide would be nice here, how to do it?` comment sat next
  to this exact line since 2020 (commit `fef9c9c0f`) and was never answered — confirmed this is
  still true on upstream `openstates-scrapers` `main` too, not a DDP-only gap.
- `openstates-core/openstates/importers/base.py`'s `resolve_person()` only ever matched on
  case-insensitive exact string equality against `name`/`other_names`/`family_name`. It never
  queried `PersonIdentifier` for vote resolution — even though that exact query pattern already
  existed elsewhere in the codebase (`cli/people.py:345`) for a different purpose. When the
  House's disambiguated `sort-field` ("Garcia (CA)", "Frankel, Lois") didn't `iexact`-match our
  stored name fields, the person silently resolved to `None`.
- `VoteEvent.vote()`/`yes()`/`no()` even had a dead, unused `id=None` kwarg already sitting there
  — this looks like it was anticipated at some point and never finished.

**Scale:** this isn't just HR 8646. Across every US Congress vote event in the local DB:
**147,473 of 534,522 person-vote rows (~27.6%) have a null `voter_id`**, across 1,535 distinct
roll calls — matching "almost every bill" from the ticket.

**VoteBot itself has no bug.** `votebot/src/votebot/services/bill_votes.py` faithfully displays
whatever party OpenStates returns (`party or "Unknown"` in `format_bill_info_document()`). The
fix belongs in the scrape/import pipeline, not VoteBot.

No `CONGRESS_API_KEY` was found configured anywhere on disk (checked every `.env` under
`~/Developer/repos/*` and `votebot/.env.example`'s placeholder) — not needed in the end, since
the free House Clerk XML endpoint was sufficient to confirm Congress.gov's own data is sound.

## Fix shipped

A contained change across two repos, using the pseudo-id mechanism that already exists for
exactly this purpose (see `bill = _make_pseudo_id(identifier=..., from_organization__classification=..., ...)`
elsewhere in the same file):

- `openstates-core/openstates/scrape/vote_event.py`: `vote()` (and `yes()`/`no()`) now accept an
  optional `id=` kwarg and fold it into the pseudo-id as `{"name": ..., "id": ...}` when present,
  instead of name-only.
- `openstates-core/openstates/importers/base.py`: `resolve_person()` now tries
  `Q(identifiers__identifier=<id>)` (scheme-agnostic — bioguide and lis values won't collide)
  scoped by the same jurisdiction/chamber/date filters as before, *before* falling back to the
  existing name-matching logic. Falls through to name matching if the identifier doesn't
  uniquely resolve, so this can only ever fill in a match, never break an existing one.
- `openstates-scrapers/scrapers/usa/votes.py`: the House (`:216`) and Senate (`:319`) call sites
  now pass `id=bioguide` / `id=lis_id` alongside the existing `note=`.

Verified end-to-end against the real HR 8646 roll call and the real local DB (read-only): all
95 previously-null vote records for that bill now resolve to the correct, distinct person via
bioguide (e.g. `Amodei (NV)` → Mark Amodei/Republican, `Barragan` → Nanette Barragán/Democratic,
`Carter (GA)` → Buddy Carter/Republican vs. `Carter (LA)` → Troy Carter/Democratic).

Tests added: `openstates-core/openstates/scrape/tests/test_vote_event_scrape.py`,
`openstates-core/openstates/importers/tests/test_vote_event_importer.py` (identifier match,
identifier-miss-falls-back-to-name), and a new
`openstates-scrapers/scrapers/usa/tests/test_votes.py` (fixture-based, no network) confirming
the bioguide/lis_id flow through the scraper unchanged. Full `openstates-core` suite (352 tests)
passes. The new logic is additive and scoped to whatever a scraper opts into passing as `id=` —
state scrapers that don't pass one are unaffected and keep resolving on name exactly as before.

## Backfill for already-scraped data

`backfill-vote-person-resolution.py` (repo root, modeled on `backfill-motion-classification.py`)
re-resolves existing null-`voter_id` rows using the identifier already sitting in the `note`
column, without re-scraping. `--dry-run` against the real local DB: **144,340 of 147,473 (97.9%)**
of currently-unresolved US vote records would resolve. The remaining ~3,100 have a `note` value
that doesn't match any known identifier (e.g. former members not in our people directory) and
are left alone rather than guessed at.

**Not yet run for real** — it mutates the production Postgres DB, so that's left as an explicit,
separate action for whoever promotes this fix, not something to fire automatically alongside the
code change.

## Promotion path (per this repo's conventions)

- `openstates-scrapers` is a formal DDP org fork — branch → PR → fork `main` directly.
- `openstates-core` uses the `cherry-pick-line` convention (est. 2026-07-25, see
  `PLAN-fork-management.md`) — branch → PR against `cherry-pick-line`, picked up automatically
  by `apply-local-patches.sh`'s range-pick on the next scrape, not a direct PR to `main`.
- This repo (backfill script + this note) — normal PR to `main`, per `CLAUDE.md`'s dev→prod
  discipline.
