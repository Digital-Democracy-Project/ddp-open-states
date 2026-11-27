# CHECKPOINT (prod agent): v99 rebuild done on EC2; Virginia 2026 re-import started. 2026-11-27 (production host)

Ramon approved this sequence in my session today: the v99 rebuild, the Virginia re-import, then broker release `7c43c6b2` (his go also waives the Voatz gate on condition Voatz stays off). I waited for the Iowa and Pennsylvania runs to finish (Iowa: 3 sessions, 0 failed, archived; Pennsylvania nightly loaded) because the ddp-sync rebuild needs every pipeline lock clear.

**Done (11:15 to 11:20 UTC)**
- api-v3 rebuilt at core `1e138376` and recreated: healthy. ddp-sync rebuilt with core `1e138376` and scrapers `10fc28a3`, recreated under the narrow rule (log saved first): healthy, 35 scheduled jobs, 0 errors in the first minutes.
- Core pin drift check: OK. The scrapers image, api-v3 and ddp-sync loader all report core `1e13837605fc107a0f0ed30c400dec23c0a656cc`.
- Rollback images kept: `ddp-sync:pre-v99-da9641d`, `ddp-openstates-api:pre-v99`.
- **Gates read on the image the pipeline launches** (tag v99, digest `c4cc4436...ee99dc`, matches your note): `grep -c -i accede` on the motion yaml 7; `ddp_yes_is_against` in `nc/bills.py` 1; `house-rollcall-num` in `ma/bills.py` 1; `resolutions? adopted` 7. All non-zero.

**Started:** Virginia `sessions=2026` with `full=true`: answered 202 with `"full": true`, 11:21 UTC, lock was empty first. I will start `2026S1` after this one loads, then the Virginia archive, and report the vote counts against your pass numbers (11,553 stored before and after; 85 Senate Accede votes lose the passage label; 38 "Agree to R" gain it).

**Not started:** Kentucky, Maryland, Missouri, Maine, Georgia dry runs, North Carolina and Massachusetts re-imports (each needs its own go from Ramon). The broker release `7c43c6b2` follows the Virginia re-import and outside the 05:00-07:40 and 08:00-08:45 UTC windows.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
