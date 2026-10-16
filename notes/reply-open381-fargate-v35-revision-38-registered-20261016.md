# Reply to the OPEN-381 Fargate request: v35 built from openstates-core 53feef5b, `ddp-scrapers` task-definition revision 38 registered (Mac session, 2026-10-16)

Done as requested, and nothing else: no task run, no revision deregistered, no schedule/flag/role/secret change, no RDS access, no recompute.

## Result

| | |
| --- | --- |
| Image | `350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v35` |
| Digest | `sha256:37255476ba72c4e2740f8a64376025feb722ca8c5994497866436d1afcc7c99d` |
| Built from | `deploy-scrapers-image.sh` (fresh clone of both forks' `main` at build time); openstates-core `main` was exactly `53feef5bdde1f277195719a9144f88f6c38fe4dc` when checked just before |
| New revision | `ddp-scrapers:38` registered 2026-10-16 04:44:27Z (before this, the latest ACTIVE was r37 on image v34) |
| Difference from r37 | **only the image** (`v34` -> `v35`); the script's check printed "everything else is IDENTICAL ... PASS" |

Ramon ran the build script in-session (it built, passed its own import check and the Utah end-to-end smoke test, and pushed; it then stopped at its interactive prompt, as last time). I registered the revision with the separate no-prompt script.

## The code proof (the request's snippet, run in the image with its own Python)

* **v35:** printed `OK /opt/openstates-core/openstates/__init__.py` (the path is inside the image).
* **v34, same snippet:** fails with `ImportError: cannot import name 'origin_chamber' from 'openstates.utils.version_ordering'`, as expected.

## Rollback (recorded)

`aws ecs deregister-task-definition --region us-east-1 --task-definition ddp-scrapers:38` makes r37 the latest ACTIVE again.

## What this means

Registering is the cutover: the next launched task (the weekly run, Sunday 2026-10-18 02:00 UTC) uses v35, so new Arizona data is archived with OPEN-368/379/382. Stored data is unchanged; that is the OPEN-381 recompute.

## About the two OPEN-381 requests on this branch

There are two recompute requests: `request-open381-arizona-final-recompute-HOLD-until-ramon-says-go-20261016.md` (`dc6da59`) and an earlier, shorter one from this Mac session (`request-open381-az-second-recompute-dry-run-now-commit-HOLD-until-ramon-says-go-20261016.md`, `35c2814`). **Follow `dc6da59`**: it has the full gates and the Part 1/2/3 structure. The only thing the earlier one adds is information, not instructions: on the Mac's copy of the production replica with core `53feef5b` the dry run printed

`az: [DRY RUN] 2190 bills checked | unchanged=6934 corrected=1982 nulled=17`

(1,247 action documents, 658 Engrossed, 82 Chaptered, 4 Conference Committee, 8 other; the 17 nulled are the 16 failed-amendment documents plus SR 1036's Kavanagh amendment, which is now the first version of a bill that has no Introduced Version). `dc6da59` says it has no expected line; treat this one as a comparison only. Your own dry-run line is the gate, and the commit still waits for Ramon's GO note.
