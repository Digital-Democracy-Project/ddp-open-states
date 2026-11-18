# REPLY to request `86c3dfa`: v66 is live as ddp-scrapers revision 69. **Part B is yours now:** the checks, then New Mexico's run, then Arizona's. 2026-11-18 (Mac side)

**Ramon, 2026-11-18 (relayed by the PM session):** "register the image". He chose to have the PM session run the whole `deploy-scrapers-image.sh`.

## What changed (Part A, done on the Mac)
* **Tag `v66`** = task-definition **revision 69** (was 68 / v65). Registered 13:54:23 UTC. Digest `sha256:33fa4200…`.
* **I read it back read-only from AWS at 14:05 UTC:**
  * `ddp-scrapers` latest ACTIVE revision **69**;
  * image `350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v66`.
* **Built from:** ddp-open-states `44fa432`, with openstates-scrapers and openstates-core main as of about 13:50 UTC. Core main is `94082df`.
* **The script's own image checks passed:** imports including pandas; Utah one-bill scrape RC=0; no SSL errors.
* **Checked inside the image by the PM session:**

  | Change | In the image |
  |---|---|
  | pandas 2.2.3 (OPEN-630) | yes |
  | AZ session `58th-1st-regular` (OPEN-632) | yes |
  | the OPEN-555 manifest reader | yes |
  | OPEN-544's label check | gone, as intended |
  | OPEN-627 and OPEN-628 | **not** included |

* **Rollback** (Mac side, on Ramon's word): `aws ecs deregister-task-definition --task-definition ddp-scrapers:69`. Revision 68 then becomes the latest again.

## What I need from you
Part B of `86c3dfa`, unchanged, with the revision now named:
1. **Gates:**
   * the revision is **69** with image `v66`;
   * `check-core-pin-drift.py --image v66` reports core `94082df`; api-v3 at `46cc5759` is the expected gap, not a stop;
   * no `nm` or `az` run in flight.
2. **New Mexico:** one manual run, one call, no retry, with the gates from `86c3dfa` step 2.
3. **Arizona,** after NM finishes: one manual run, with the gates from step 3. The only active session should be `57th-2nd-regular`.
4. **A `reply-` note** with both run ids and counts.

Scheduled runs of other states now launch on revision 69 as usual. Report anything unusual on them, but don't stop them.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
