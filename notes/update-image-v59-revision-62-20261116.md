# Update: scrapers image v59 is LIVE as `ddp-scrapers:62` (step 2 of `9963ec8` done). Steps 4 to 8 may start. 2026-11-16 02:31 UTC (Mac side)

**Ramon, 2026-11-16 ~02:30 UTC: "check ops-handoff and then register the image".** That followed your `49ee4fb` (migration `data.0050` applied 01:26 UTC).

## What is live
* **Image:** `350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v59`, digest `sha256:95ed632ef16a22d1e1a4d73f1c02deb8914fc942eeaa85db1c33fac707e179c6`.
* **Task definition:** `ddp-scrapers:62`, registered 02:31:23 UTC (was 61 = v58). Everything else in the definition is copied from 61, exactly as `deploy-scrapers-image.sh` does.
* **Code** (cloned from main at build time): ddp-open-states `5f945b0` (#374 merged), openstates-core main `eec94082b`, openstates-scrapers main `e13dbe424`. The script's build log shows the fresh clones; v59 contains every PR listed in `9963ec8`.
* **Checks before register:**
  * the script's own checks: Python 3.13.18, imports OK, and a one-bill Utah smoke scrape (RC 0);
  * **my smoke test inside v59:** `os-text-extract --help` starts (the #101 regression is fixed), and `reverse-action-order --help` and `remove-stale-documents --help` both print their usage.
* **Rollback (Ramon):** `aws ecs deregister-task-definition --region us-east-1 --task-definition ddp-scrapers:62`. That leaves 61 (v58).

## Timing
* **Washington's 02:30 nightly** launched before the register, so it runs on revision 61.
* **The first runs on 62** will be **usa 03:00** and **pa 04:00** (pa is also OPEN-477's stall-check test). Please name the revision of each in the nightly report.
* **Louisiana and Nebraska:** per your `49ee4fb`, nothing runs them before Sunday 11-22 02:00 UTC unless someone triggers them. **Do not trigger them**; step 6 must finish first.

## Go ahead
Steps **4, 5, 6, 7 and 8** of `9963ec8`, in order. Each is saved **only if its dry run passes its gate**; stop and report on any failed gate.
* **Run the steps with v59's code.** Use the image, or core `eec94082b`, which is what v59 carries, as you prepared. If you use the host venv (Python 3.9.2), say so per step; v59 itself is 3.13.
* **Step 6.4:** ddp-open-states main (`5f945b0`) already carries #374 (la/ne back to `false`). **Pull and roll it out only after both flips have committed.** Until then the checkout stays at `dead3de7`, which has la/ne `true`; the flip's `--manifest` reads that.
* **Step 6.5:** there is no scheduled broker bill-event task on production, so there is nothing to re-bootstrap. Noted.

## Your A3 answer (the Mac replica and `ddp_bill_document_not_found`)
Nothing on the Mac reads that table; only the archiver writes it, against RDS. **Leave the publication as it is.** No change on the Mac.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
