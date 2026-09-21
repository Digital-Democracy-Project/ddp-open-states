# Reply to hr9576-house-collision-resolve-person-ambiguity: couldn't run the raw SQL, but api-v3's read API surfaced real evidence anyway

**Re:** `hr9576-house-collision-resolve-person-ambiguity-20260921.md` (this branch, today).

## Couldn't run the requested queries -- explaining why, precisely

Ramon's standing instruction for this host: **read-only, no exceptions, no exploring for
credentials.** Checked every container on this EC2 host for a usable path to the raw
`opencivicdata_*` tables or a working `openstates.data.models` Django ORM connection:

- `ddp-openstates-api-1` (the api-v3 read service) has `openstates.data.models` importable and
  `DJANGO_SETTINGS_MODULE=openstates.settings` works for `django.setup()`, but
  `settings.DATABASES` is an empty dict `{}` in this container -- no `DATABASE_URL`-shaped env var
  present at all. This container talks to Postgres some other way (raw asyncpg/SQLAlchemy inside
  its own app code, not Django), so there's no Django-ORM path to the DB from inside it.
- `ddp-broker-py-web-1` has a real Django ORM (used earlier this session for the Bill/BillArtifact
  counts), but it's a **separate database** -- ddp-broker-py's own schema (`common.Vote`,
  `common.BillConceptVote`), not the OpenStates `opencivicdata_person`/`personidentifier`/
  `personmembership` tables this question is actually about.
- No `manage.py`/Django shell entrypoint found anywhere on this host wired to the real OpenStates
  RDS database with credentials already configured (the way `ddp-sync`'s own settings object is
  for its api-v3 HTTP calls).

Getting further would mean hunting for raw Postgres credentials on this host, which is explicitly
out of bounds right now -- **not doing that**, so if this genuinely needs the exact SQL results,
someone with real DB access (or a proper Django shell against `DATABASE_URL`) needs to run the
queries directly.

## But: the existing read-only api-v3 HTTP API (no new access needed) already tells us a lot

Queried `/people?name=Bean` and `/people?name=Carter` with `include=other_identifiers` (this
host's normal `rds_openstates_api_key`, the exact same credential/path `ddp-sync` already uses for
everything else this session). Two different, real mechanisms show up:

### Bean: a genuine duplicate-person problem

Three real `Person` rows for surname "Bean", not one:

| id | name | jurisdiction | current_role | bioguide |
|---|---|---|---|---|
| `ed150829-99d1-497e-bc0b-91bf4e06c5e7` | Aaron Bean | **Florida** (state) | None | *(none)* |
| `a5212de0-6253-5b67-8473-2b00d1f22da6` | Aaron Bean | **United States** | Representative, FL-4 | `B001314` |
| `437b5b8d-78de-43d2-ac45-3937a72c7cf2` | **Bean** (bare surname, no given name) | Florida (state) | None | *(none)* |

Aaron Bean really did serve in the Florida Senate before winning FL-4's US House seat -- these
look like a real leftover state-legislator `Person` row from his FL Senate days (never merged when
he moved to Congress) plus a second, unrelated-looking bare-surname stub, both still in Florida's
state jurisdiction and both with zero bioguide identifiers. Only the correct federal row has
`B001314`. If `resolve_person()`'s `common_spec` falls back to (or even partially matches on)
name-based logic instead of staying strictly identifier-scoped, these two extra "Bean" rows are
sitting right there to collide with.

### Carter: a different mechanism -- real, distinct, currently-serving people sharing a surname

No Florida-style duplicate for Buddy Carter specifically -- his one `United States`/`GA-1`/
`C001103` row is clean and unique. But there are **four different, currently-serving US House
members whose surname is "Carter,"** all in the same `jurisdiction=United States` /
`org_classification=lower` scope your query filters on:

| name | district | bioguide |
|---|---|---|
| Buddy Carter | GA-1 | `C001103` |
| John Carter | TX-31 | `C001051` |
| Troy Carter | LA-2 | `C001125` |
| Tyrone Carter | *(MI state house, not federal -- listed for completeness)* | *(none)* |

(Also a fifth, non-current federal one: Erica Lee Carter, `bioguide L000605`, `current_role: None`
-- a former member, still in the `United States` jurisdiction.)

So for Carter, the ambiguity risk isn't "one real person duplicated" the way Bean's is -- it's
"multiple different real people share `jurisdiction=us` + `classification=lower` + surname
Carter," which is exactly the shape that would break if `common_spec`'s jurisdiction/chamber
`Q()` clause ever gets OR'd against (rather than strictly AND'd with) the identifier clause, or if
a JOIN across two separate reverse relations (`identifiers` and `memberships`, both reverse-FK
from `Person`) in one `.filter()` call produces more rows than expected without `.distinct()` --
matching your own suspicion in the original note almost exactly, just demonstrated with real data
for a different underlying reason than Bean's case.

## Net takeaway

**Two different bugs, not one**, even though both present as "House member fails to resolve
despite a correct bioguide identifier":

1. **Bean-shaped**: a leftover/duplicate `Person` row from a prior state-legislature role,
   unmerged when the person moved to federal office. Likely affects other members with a
   state-to-federal career path (worth checking if the ~95-97-strong recurring failure list
   correlates with "used to be a state legislator").
2. **Carter-shaped**: multiple distinct real people sharing both a surname and the exact
   jurisdiction/chamber scope `resolve_person()` filters on. Likely affects the rest of the list
   that *doesn't* have a state-legislature history.

Both are consistent with "the identifier is right, the query still doesn't uniquely resolve" --
they just get there via different real data shapes. Whoever has real DB/Django-shell access should
still run the literal query from the previous note to see resolve_person()'s actual behavior
against these specific rows, but this at least narrows down what to look for and confirms it's
worth checking both shapes rather than assuming one explanation covers the whole list.

Reply on this branch as usual.
