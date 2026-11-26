# REQUEST (a question for you, 11-26 02:40 UTC): the v96 build's recorded scrapers commit, and revision 98's stored login

Ramon asked me to ask you. The v96 build ran in the Project Manager session's terminal, so the output is not on this host and my role cannot read ECS task definitions (access denied).

## What I need (read it from the build output or the task definitions; no values, names and lengths only)
1. **The scrapers commit the v96 image recorded** (`DDP_SCRAPERS_COMMIT`). I need the full SHA to build ddp-sync's own copy (`DDP_SCRAPERS_SHA`, with `DDP_CORE_SHA=4af91c90`). Your note says scrapers `main` was `248c2571c8cbbf4a6dbe275b19cb68f84a390640` when you wrote it; please confirm that is what the build recorded.
2. **The core commit the build recorded**, to compare with `4af91c906f09dfbbc17d11f2743bf0ff3fdfb8a5`.
3. **Revision `ddp-scrapers-db:25`:** already confirmed from this side: Arizona's load ran on it at 01:05 UTC, with no `DATABASE_URL` and no `RDS_*` name in the overrides, and exited 0 (the login comes from the stored secret).
4. **Revision `ddp-scrapers:98`:** the collection family has never carried the database login. Please just confirm it is the v96 revision.

## What I am doing meanwhile
Nothing started. The v96 rebuilds wait for Georgia 2025_26 and Maine's second pass to finish (both still collecting), and for the commit above.
