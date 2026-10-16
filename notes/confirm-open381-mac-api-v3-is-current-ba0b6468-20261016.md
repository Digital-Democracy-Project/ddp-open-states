# CONFIRM: the Mac's api-v3 is on `ba0b6468` (OPEN-381, Mac side, 2026-10-16 04:46 UTC)

The Mac's api-v3 (`ddp-openstates-api-1`, :8002, serving the production replica) was refreshed by Ramon in-session with `refresh-api-v3.sh` from `5a0ee98` to **`ba0b64685b2eab50bf605c6eec29ace99ce7bf0a`** (`ba0b6468`, api-v3 #31, which includes #30). Scoped to the `api` service only; the script confirmed `ddp-openstates-postgres-1` untouched; healthy 6 seconds after start (container started 04:46:34Z).

**Checked on the deployed code** (inside the running container, its own `api.version_ordering` and the database, not through the HTTP route, because that needs an API key I did not pull out of the profile table): Arizona `HB 2014` (57th-2nd-regular) orders as `Introduced Version`, `HOUSE - Natural Resources, Energy & Water`, `HOUSE - Appropriations`, `House Engrossed Version`, `SENATE - Natural Resources`. Before this change the House Engrossed Version came right after Introduced and every action document after it. This is the example `dc6da59`'s Part 2 uses for the prod agent's own instance.

**Rollback caveat:** no rollback image tag exists for `5a0ee98` (my tagging step was part of the command that was denied first, and the refresh then overwrote `ddp-openstates-api:local`). To roll the Mac back: `git checkout 5a0ee98` in `api-v3` and rerun the refresh. The older tag `rollback-14d3073` is two versions back and should not be used.

This satisfies the Mac-side condition in `dc6da59` ("Part 3 must not start until a note confirms the Mac's api-v3 is on ba0b6468"). It does **not** authorize anything: Part 2 (the prod agent's api-v3) and Part 3 (the recompute) still need a GO note from Ramon, and the new `ddp-scrapers` revision 38 (v35) was already registered (`25798b8`).
