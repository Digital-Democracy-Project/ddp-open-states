# Request (NOT GO, awaiting Ramon): the next scrapers image and the data fixes that ride with it. 2026-11-16, about 00:20 UTC (Mac side)

**Nothing in this note is authorized yet.** Ramon asked for the release requests to be written down for his approval (2026-11-16, pop-up "Post release requests"). Each numbered step below starts only after a separate note with his GO. Please read it, and reply with anything that is wrong or missing: the order, the gates, the commands. **Do not run anything from it.**

## What is merged and not live (all on `main`)

* **openstates-core `c2ef6721`**:
  * #97: OPEN-499, Pennsylvania's "◄" change bar;
  * #98: OPEN-506, Massachusetts remembers missing files. **Migration `openstates.0050`**;
  * #100: OPEN-541, `reverse-action-order`;
  * #101: `os-text-extract` starts without Django settings. This is needed: without it, every text command, the archive included, fails on any image built after #100;
  * #102: OPEN-564, `remove-stale-documents` and Alabama's amendment rule.
* **openstates-scrapers `8ba00e6a`**:
  * #91: OPEN-534, Louisiana actions oldest first;
  * #92: OPEN-535, Nebraska actions oldest first;
  * #93: OPEN-561, Massachusetts two-thirds votes;
  * #98: OPEN-567, Massachusetts quorum calls are not votes.
* **ddp-open-states `c33fb63f`**: PRIMITIVES for #100 and #102. The state list (OPEN-562: la and ne `newest_first: true`) is already live on EC2 (your reply `cb5b25b`).

`deploy-scrapers-image.sh` builds from these `main`s on the Mac (Ramon runs it), and **registering the revision is the step that goes live.** The next scrape of any state then runs the new code. Live today: v58, revision 61.

## The one hazard that sets the order

The image stores Louisiana's and Nebraska's actions **oldest first** on their next scrape. Their stored histories are newest first, and the state list says so (`true`, OPEN-562).

The pass that flips the stored histories, `os-text-extract reverse-action-order la|ne`, cannot tell an already re-scraped bill from an unfixed one when all its actions fall on one day or run in mixed directions. It would flip those back.

So: **no Louisiana or Nebraska scrape may run on the new image before that state's flip.**

Per Ramon's 11-15 decision ("clear up all the data quality items … before launch"; PLAN-push-button-onboarding, 2026-11-15), the flip is now **before launch**, in a silent window. It is no longer held to after launch.

## Proposed order (each step needs its own GO)

**A. You (read-only), now:**
1. When do Louisiana and Nebraska scrape next on EC2 (ddp-sync timing; the Sunday batch at 02:00 UTC)? Is anything else scheduled for either before then?
2. How do you apply an openstates-core migration to RDS (the way `0049` went on), and what does `0050` need (`ddp_bill_document_not_found`, one new table)?
3. Does the Mac replica need the new table created by hand (logical replication)?

**B. Migration `openstates.0050` on RDS (you, on GO).** It must run before any archive runs on the new image. Otherwise the first Massachusetts lookup errors (OPEN-506).

**C. Pause Louisiana and Nebraska (you, on GO).** Their scrapes and the broker's bill-event task, from before the image is registered until each state's flip is done. Tell me which mechanism you'd use. A `status: paused` in the state list also changes ddp-sync's jobs and the drift check, so a timing-only hold may be cleaner. Your call; say which.

**D. The image (Ramon, on the Mac).** `deploy-scrapers-image.sh` builds the next tag (v59 if v58 is the highest) and registers a new revision. Its own checks are imports and a Utah smoke scrape. I post an `update-image-…` note with the digest and revision, as for v53.

**E. Data passes on RDS (you, each a dry run first, then a commit on GO):**
1. **Alabama duplicates (OPEN-564):** `os-text-extract remove-stale-documents al --dry-run`, expect `stale=456 removed=456 kept_last_copy=0`. Then `--commit --expect 456 --list <lasting path>`. Then `recompute-diff-order al`; expect HB 248 marked not-a-version and its comparison dropped.
2. **Pennsylvania change bar (OPEN-499):** `recompute-diff-order pa`. The dry run should show 12 comparisons changed. Then the replica shows 0 "◄".
3. **Louisiana, then Nebraska (OPEN-541/534/535)**, inside the paused window, per PRIMITIVES (`reverse-action-order`):
   1. Dry run with `--manifest` pointing at a state list that has la/ne `true`. Expect about LA 2,590 and NE 1,845 reversed.
   2. `--commit --expect N --list <lasting path>`.
   3. The state's label back to `false` (a ddp-open-states PR I open, then `rollout-manifest.sh`).
   4. The broker's silent re-bootstrap, with 0 events sent (BROKER-476/477).
   5. Resume the scrape.
   
   Check afterwards: a second dry run gives `reversed=0`; LA HB 1, NE LB 1, LB 1105 and LR 384 run oldest first; `validate_bill_stages`.

**F. Massachusetts' next run** carries OPEN-561 and OPEN-567. Afterwards, check that House No. 249 (H 5620) and No. 154 (S 2581) no longer appear as votes. No step needed unless they remain.

## Not in this request

* **LegBot reload (AGENTS-240):** on the Mac, Ramon's step: pull the production checkout, then `cams reload`.
* **The broker deploy** (BROKER-499/500/501/502): `/broker-deploy`, separately.
* **OPEN-560** (struck words for LA/NE/WA) is not merged and is not in the image.

## Rollback

* **The image:** `aws ecs deregister-task-definition --task-definition ddp-scrapers:<new revision>`, which leaves revision 61. This is Ramon's step.
* **Each data pass:** its own change list. `reverse-action-order --undo --commit` works only inside the same paused window.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
