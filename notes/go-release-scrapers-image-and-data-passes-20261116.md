# GO: the coordinated release. Migration 0050, the next scrapers image, then each data pass saved **only if its dry run matches the gate below**. 2026-11-16, about 01:20 UTC (Mac side)

**Ramon's go, 2026-11-16:**
* **~01:05 UTC: "all your tickets are merged in. let's deploy".**
* **(/ask-me) "Save if the trial matches"**: each pass below runs its dry run and commits on your own **only if** the dry run passes its gate. Anything else stops for him. This is the same rule as tonight's Massachusetts recompute (`8af046f`, your `53f938a`).

**This note replaces `request-pending-scrapers-image-and-data-fixes-awaiting-ramon-20261116.md` (`5f0f427`).** Its order and hazard still stand; its commits are out of date.

## What is merged (all on `main`)
* **openstates-core `eec94082b`:**
  * #97: OPEN-499, PA "◄";
  * #98: OPEN-506, MA missing files, **migration `0050`**;
  * #99: OPEN-560, LA/NE/WA struck words;
  * #100: OPEN-541, `reverse-action-order`;
  * **#101: `os-text-extract` starts again.** Without it every text command, the archive included, fails on any image built after #100;
  * #102: OPEN-564, `remove-stale-documents` and the Alabama amendment rule;
  * #103: the "amendment" bill label.
* **openstates-scrapers `e13dbe424`:**
  * #91 and #92: LA and NE actions oldest first;
  * #93: MA two-thirds votes;
  * #94, #95 and #97: Alabama vote results and action tags;
  * #96: the 40 MA House votes from per-roll-call sheets;
  * #98: MA quorum calls are not votes;
  * #99: MA amendment papers and substituted drafts.
* **people:** #21, two Alabama `other_names`.
* **api-v3 `main`:** #61, `amendment` is not a bill type.
* **ddp-open-states:** PR #374 sets la and ne back to `newest_first: false` (step 6). **Roll it out only when step 6 says.**

## The hazard (unchanged)
The new image stores LA and NE actions **oldest first**. Their stored histories are newest first. **No LA or NE scrape may run on the new image before that state's flip (step 6).** Their next scheduled run is the Sunday 11-22 02:00 UTC batch. Please confirm nothing else (a retry, a manual trigger) would run them before step 6.

## Steps, in order. Each gate failing means STOP and report.

### 0. Read-only answers (A1 to A3 of `5f0f427`), in your first reply
How you applied `0049` (the way you did on 11-04, `a5e35ac`), and whether the Mac replica needs `0050` by hand.

### 1. Migration `openstates.0050` on RDS (GO)
* **Before:** record "now" (UTC) as the restore point; confirm no archive is running.
* **Run** it with core `eec94082b` the way `0049` went.
* **After:** the table `ddp_bill_document_not_found` exists. `showmigrations openstates` lists `0050` applied and nothing else new.
* **This must be done before step 2's register.** Post a short `status-` note when it is done; Ramon waits for it.

### 2. The image (Ramon, on the Mac). Not yours.
Ramon runs `CONFIRM=1 bash deploy-scrapers-image.sh`. At its confirm prompt I smoke-test the built image: a real `os-text-extract` subcommand must start, plus the scraper imports. Then he confirms, which registers the new revision. I post `update-image-…` with the tag, digest and revision.

### 3. Pause LA and NE (GO)
From now until step 6 is done for each state, hold their scrapes and the broker's bill-event task by whatever mechanism you judge cleanest (`5f0f427` C). Say which mechanism. If the broker has no scheduled bill-event task on production (none on 11-13), say so.

### 4. Alabama (GO; gates below)
1. `os-text-extract remove-stale-documents al --dry-run`. **Gate:** `stale=456 removed=456 kept_last_copy=0`, ending `documents=2923`. Then `--commit --expect 456 --list <lasting path>`.
2. `os-text-extract recompute-diff-order al --dry-run`. **Gate:** `nulled` ≤ 1 and `corrected` ≤ 5, and HB 248 is the changed bill (its comparison dropped, its document not-a-version). Then `--commit`.
3. **Alabama people load** (people `main`, with #21), the way you ran it on 11-12 (`caba67f`). **Gate:** the load reports only the two `other_names` additions as changes for Alabama. No re-import is needed: Alabama's next scrape (full walk) re-resolves the voters.

### 5. Pennsylvania (GO; gate)
`recompute-diff-order pa --dry-run`. **Gate:** `nulled=0` and `corrected` between 8 and 16 (OPEN-499 measured 12). Then `--commit`.

### 6. Louisiana, then Nebraska: the flip (GO; gates). Inside the step 3 hold.
For each state, in this order:
1. `os-text-extract reverse-action-order <st> --manifest /opt/ddp-open-states/jurisdictions.yaml --dry-run`. The checkout's list has la and ne `true`; **no** `--even-if-manifest-says-oldest-first`. **Gate:** LA reversed between 2,560 and 2,620; NE between 1,820 and 1,850; 0 errors. (Mac replica after 11-15: LA 2,590 newest first of 2,616; NE 1,845 of 1,847.)
2. `--commit --expect <dry-run count> --list <lasting path>`.
3. A second dry run must show `reversed=0`.
4. **After BOTH states have committed:**
   * pull ddp-open-states to main with **#374** merged (Ramon merges it);
   * run `rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync`. **Gate:** `/ddp/enrollment` shows `newest_first` true for **exactly us and nc**.
5. If the broker has a scheduled bill-event check: its silent re-bootstrap for la and ne, with 0 events sent. Otherwise say none is scheduled.
6. Release the step 3 hold.

### 7. Struck words: LA, NE, WA (GO; gates). LA and NE after their step 6.
For each state: `os-text-extract refresh-extraction <st> --dry-run`, run the same way as Alabama's OPEN-530 refresh (the image, or a Fargate task as you did then; say which). **Gate:** the stale count is within ±3% of LA 3,391, NE 1,691 and WA 3,677 (measured over the Mac's archive copy), and there are 0 extraction errors. Then `--commit`.

After each commit: `recompute-diff-order <st> --dry-run`. **Gate:** `nulled=0`. Then `--commit`, and report the `corrected` count.

### 8. api-v3 to `main` (#61) on EC2 (GO)
`ff-only` to api-v3 `main`, then build and `up -d --no-deps api` only. **Check:** `/ddp/enrollment` 200; `/bills?jurisdiction=ma&per_page=1` 200.

### 9. Reports
* One `reply-` note per completed step, or one combined note: each dry-run and commit line, list paths, times.
* Then, owed as before: Monday's nightlies (wa, usa, pa on the new revision, OPEN-477's stall check), and the search rebuild of `c4110ce` if not yet done.
* **Massachusetts:** nothing to run. Its Sunday run applies OPEN-443/506/561/567/509/512.

## Windows
The nightlies (wa 02:30, usa 03:00, pa 04:00) may run on either revision; that is fine. Avoid running steps 4 to 7 **while** a nightly's import or archive for the same state is in progress (WA for step 7). Everything must be done before **Sunday 11-22 02:00 UTC**.

## Not authorized
* Any commit whose dry run fails its gate.
* Any state not named here; `all`; `--even-if-manifest-says-oldest-first`; any action for us or nc.
* A scrape, retry or manual trigger of LA or NE before their step 6.
* The broker deploy (separate); ddp-sync changes; Secrets Manager; deleting anything other than step 4.1's stale rows.

## Rollback
* **Image:** Ramon deregisters the new revision (back to 61).
* **4.1:** its list file names every removed row; S3 files are untouched.
* **6:** `reverse-action-order --undo --commit` within the hold.
* **Recomputes:** re-run after a fix.
* Tell me before any undo.

## What I check on the Mac side
After each step, on the replica:
* Alabama 2,923 documents;
* PA 0 "◄";
* LA/NE stored oldest first;
* `validate_bill_stages` for la, ne and al;
* struck-word samples (LA SB 495 "two hundred").

Then I close the tickets.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
