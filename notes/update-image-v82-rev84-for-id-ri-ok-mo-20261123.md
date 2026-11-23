# UPDATE (not a GO): **image v82 is built**: task revisions **ddp-scrapers:84** and **ddp-scrapers-db:11**, core **`939e4a2c`**, scrapers main **`4e22ce72`**. It satisfies the "image" step of my Idaho, Rhode Island and Oklahoma requests (and Missouri's, on ddp-sync). 2026-11-23 (Mac side, Onboard New States)

**Not a GO.** Each request's other steps and gates stand. Only its image step now names a real revision. Ramon built v82 (relayed by the PM session); please confirm the newest registered revision is 84 when you next read ECS.

**Checked:** scrapers `4e22ce72` contains (GitHub compare, each "ahead"):
* `02ba6f4e` (ID #234);
* `a49913ae` (ID #242);
* `2688a473` (RI #235, #236);
* `c29cfa4f` (OK #237, #238);
* `c3ec462d` (MO #239);
* `29be4a1b` (NC #233).

Core `939e4a2c` holds RI #140 and OK #141.

| Request | Its image step now reads |
|---|---|
| Idaho `7788700` / `9b4d8b9` / `c77027a`, step 2 | **done: v82 = rev 84.** Step 3's gate 2 is "new tasks run rev 84 or later" |
| Rhode Island `98e5dcb`, step 3 | **done: v82 = rev 84.** Step 5's gate 2 is rev 84 or later |
| Oklahoma `8108de3`, step 3 | **done: v82 = rev 84.** Step 4's gate 1 is rev 84 or later |
| Missouri (ddp-sync `4ce63e0`) | its "image containing `c3ec462d`" gate is met by rev 84 |

**The order stays as written.**
* **Idaho:** step 1, the people refresh for `id` (target `d1acd229`, expect created 17 / updated 5), still comes **before** step 3's re-import. It is now also before any weekly Idaho run on rev 84; otherwise that run would leave the substitutes' votes unlinked.
* **Rhode Island:** step 2 (manifest, pull first) and step 4 (people `ri`) come before step 5.
* **Oklahoma:** step 2 (manifest, pull first) comes before step 4.

**The weekly Sunday run (11-29 02:00 UTC) will use rev 84** for ID, RI, OK and the other weekly states. For ID, RI and OK that weekly run is incremental, so it isn't a substitute for the full re-imports.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
