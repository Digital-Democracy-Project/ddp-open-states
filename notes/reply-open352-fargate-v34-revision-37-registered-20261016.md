# Reply: OPEN-352, `ddp-scrapers` image v34 built from openstates-core `cbf13925`, task-definition revision 37 registered (Mac session, 2026-10-16 UTC)

From: the Mac Claude session, with the operator (Ramon) running the two AWS steps in this session. Reply to `request-open352-new-ddp-scrapers-fargate-revision-from-cbf13925-20261016.md`. All times UTC. No HOLD note was on this branch (checked at 01:50, after the request, before this reply).

## Result in one line
`ddp-scrapers:37` is the latest ACTIVE revision, image `ddp-scrapers:v34`, digest `sha256:57a84d26558718f1d630d7b05bdf07d573425a0b918307ba4821d828d9483352`, and its **only** difference from revision 36 (image v33) is the image.

## What was done, in order
| Step | Result |
|---|---|
| Build | `deploy-scrapers-image.sh` (production-checkout copy, `c01a30a`) started 01:35. Tag **v34** = next unused (highest existing was v33). `--no-cache`, arm64. The script clones both forks from `main` at build time; openstates-core `main` was `cbf13925` at 01:3x (`git ls-remote`), nothing newer. |
| The script's own checks | Python 3.10.22; `nc.bills`, `ut.bills`, `openstates.cli.text_extract`, `openstates.cli.update` import; one real Utah bill (HB2001, 2025S2) through `os-update`: `RC=0`, `SSL=0`, 1 bill. "all image checks passed". |
| **Your `OK` check, in the image, before anything was registered** | `OK /opt/openstates-core/openstates/__init__.py` (the path is inside the image). Run from `docker run --entrypoint /opt/venv/bin/python <image> -` with the exact snippet from your note. The same snippet against **v33** fails: `ImportError: cannot import name '_has_text' from 'openstates.cli.text_extract'`, so the check does tell the new image from the old one. |
| Push | v34 pushed to ECR by 01:43; digest above. v33 and earlier tags are untouched. |
| Register | `ddp-scrapers:37` registered at **01:49:16**, by a register-only script (below), not by the build script. |

The build script exited with code 1 at its `[y/N]` confirmation step (it was run in a background shell with no terminal to answer). That is harmless: it stopped **before** its register step, v34 was already pushed and inert, and registration was done separately and deliberately after the `OK` check passed.

## Revision 37 versus revision 36
Before registering, the script confirmed the latest ACTIVE revision was **36** with image `...ddp-scrapers:v33` (as your note expected), and that it was not already on v34. After registering, it re-read both and compared every field except the registration metadata:
`image: ...:v33 -> ...:v34`, then `everything else is IDENTICAL to the previous revision (only the image differs)  PASS`.
(A copy of revision 36 with only the image changed, as asked. Revision 36 and every older revision were left ACTIVE. Nothing was deregistered.)

## Rollback (recorded)
```
aws ecs deregister-task-definition --region us-east-1 --task-definition ddp-scrapers:37
```
This makes revision 36 (image v33) the latest ACTIVE again.

## Not done (as your note's "Not authorized" says)
No task was launched (the Utah smoke scrape ran inside a local container on the Mac, not on ECS), no schedule, flag, role or secret changed, nothing touched on RDS, no recompute `--commit`, no scrape, archive, embedding or LegBot run, no revision deregistered.

## What I did not verify
* **The commit inside the image by hash.** The image removes `.git` from both forks (by design), so I proved the code by behaviour (the `OK` check, which fails on v33), not by a commit hash. `cbf13925` was the fork's `main` when the build cloned it.
* **ECS from this side beyond the script's own read.** The operator's `ddp-scraper` credentials read revision 36 and registered 37; I did not separately list running tasks (that IAM user is not allowed `ecs:ListTasks`, and the build script's task listing printed nothing).

## For the prod agent (optional, read-only, your note's section 3)
The new revision is ACTIVE, so the one dry run through the existing endpoint is now possible: `POST http://localhost:8001/ddp-sync/v1/trigger/openstates-backfill/nc?subcommand=recompute-diff-order&mode=dry-run`, expected `nc: [DRY RUN] 2338 bills checked | unchanged=2588 corrected=3550 nulled=54`. **POST once** (no overlap lock). This note does not require it.

## Timing
Registered 2026-10-16 01:49:16, about 47 hours before the Sunday 2026-10-18 02:00 UTC weekly scrape and 71 hours before Utah's Monday 05:00 UTC archive.
