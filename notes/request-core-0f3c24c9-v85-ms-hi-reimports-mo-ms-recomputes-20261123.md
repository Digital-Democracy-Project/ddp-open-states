# REQUEST (not a GO): one release for Mississippi and Hawaii, replacing the commits in `c639029`. (1) core **`0f3c24c9`** on both api-v3 copies and EC2 ddp-sync, (2) image v85 (Ramon), (3) the Utah canary from `3e6c766`, (4) full re-imports of Mississippi and Hawaii, (5) Missouri and Mississippi recompute **dry runs** (and Hawaii's, report only). 2026-11-23 (Mac side, Onboard New States)

**Not a GO.** Steps 1, 3, 4 and 5 each wait on Ramon's go. Step 2 is Ramon's build. Every recompute **commit** waits on a second go after he has seen the dry-run numbers. Everything else in `3e6c766` and `c639029` still applies: step 0's questions, the Utah canary rules, watching Georgia, the Missouri ranges and the "Not authorized" lists. This note only moves the commits forward and adds Mississippi and Hawaii.

## Why
* Hawaii's first scrape fails two Stage 3 gates on the Mac replica (OPEN-668):
    * versions with no stage: 11,369 / 11,369 (100%);
    * unmatched sponsors: 2,160 / 33,134 (6.5%).
* Mississippi's first scrape fails the same two (OPEN-669):
    * versions with no stage: 4,014 / 6,542 (61.4%), all named "Current version";
    * unmatched sponsors: 1,297 / 7,681 (16.9%).
* The fixes are reviewed and merged by the PM session:

| Merge | What |
|---|---|
| core #146 → `2013b4a0` (OPEN-807) | new `openstates/ddp_states/ms.py`: Mississippi's amendment papers and amendment reports become not-a-version |
| core #145 → **`0f3c24c9`** (OPEN-804) | new `openstates/ddp_states/hi.py`: the order of Hawaii's House, Senate and Conference drafts |
| scrapers #253 → `3cf35ce6` (OPEN-807) | Mississippi keeps the stage names ("As Introduced", "Committee Substitute", "As Passed", "Approved by the Governor") instead of "Current version" |
| scrapers #255 → `52a40c03` (OPEN-808) | Mississippi sponsors matched by name and chamber |
| scrapers #254 → `323000c4` (OPEN-804) | Hawaii names its texts by stage ("Introduced", "House Draft N", "Senate Draft N", "Conference Draft N"); governor's messages, proposed drafts and floor amendments become documents |
| scrapers #256 → **`14c4e1c4`** (OPEN-805) | Hawaii keeps "LEE, C." as one sponsor (no names in code); the governor becomes the organization "Office of the Governor" |

* **Core since `fd486fa4` is only #146 and #145. No migration.**
* **Checked on the Mac replica (me, read-only):** all 42,299 stored (state, version name, chamber) combinations were run through `note_stage` and each state's own ordering rule, on `fd486fa4`, `2013b4a0` and `0f3c24c9`.
    * Only Hawaii's change: 11,369 combinations, all Hawaii.
    * Missouri's numbers in `c639029` therefore still stand on `0f3c24c9`.

## Step 1: core `0f3c24c9` (on a GO)
* `3e6c766` step 1 as amended by `c639029`, with **`DDP_CORE_SHA=0f3c24c9d8bdf8766e369273ffd8946b6c6f1ab4`**.
    * EC2 api-v3: tag a rollback image, build, then `up -d --no-deps api`.
    * EC2 ddp-sync, rebuilt at its current commit.
    * Mac api-v3: `refresh-api-v3.sh`, done by Ramon or me.
* **One rebuild covers all of these: OPEN-800 (certificate checks), OPEN-806 (MO), OPEN-807 (MS) and OPEN-804 (HI).**
* Same rules as before:
    * post the in-flight list before restarting ddp-sync;
    * never 02:15–04:45 UTC;
    * api-v3 never 05:00–07:00 UTC.
* Then `check-core-pin-drift.py --image-core 0f3c24c9…` exits 0.

## Step 2: image v85 (Ramon)
* Build at scrapers main **`14c4e1c4` or later**, with core **`0f3c24c9`**.
    * `14c4e1c4` holds all four MS and HI fixes, and OPEN-803 (`a121b5dd`).
    * OPEN-803 needs core `58205e01` or later, so never ship v85 on an older core.
* Mac side checks that `DDP_CORE_COMMIT` is `0f3c24c9`.
* **One possible addition, if it merges before v85 is built:** a small follow-up recording Mississippi's governor as "Office of the Governor", as Hawaii does (OPEN-808; the PM agreed). Don't wait for it: Mississippi passes the sponsor gate without it.

## Step 3: the Utah canary first (`3e6c766` step 3, on a GO)
* v85 is the first image with every request checked, so **Utah runs first on v85**, as written there.
* **A certificate error stops everything below.**

## Step 4: Mississippi and Hawaii full re-imports (on a GO, after steps 1–3)
### Gates
1. New tasks run v85's revision or later.
2. The state's `ddp:pipeline_lock:<st>` is empty.
3. Not on Sunday from 02:00 UTC.
4. One heavy load at a time.

### The runs
```
POST /ddp-sync/v1/trigger/openstates-scrape/ms?full=true&sessions=2026,20261E
POST /ddp-sync/v1/trigger/openstates-scrape/hi?full=true&sessions=2026
```
* Each answer must be 202 with `"full": true`.
* Report for each:
    * the run id and revision;
    * `"mode": "full"`;
    * bill, version and vote counts (expect about 4,124 bills for MS and about 6,728 for HI);
    * the archive result.
* No people refresh is needed: the alternate names these fixes use are already loaded.

### Pass/fail after (read-only)
```sql
-- 1. version names, per state (replace :st with 'ms' or 'hi')
SELECT bv.note, count(*) FROM opencivicdata_billversion bv JOIN opencivicdata_bill b ON b.id=bv.bill_id
JOIN opencivicdata_legislativesession s ON s.id=b.legislative_session_id
WHERE s.jurisdiction_id='ocd-jurisdiction/country:us/state:' || :st || '/government'
GROUP BY 1 ORDER BY 2 DESC LIMIT 25;
```
* **Version names:**
    * MS: no "Current version"; "Approved by the Governor" is present, about 435 times.
    * HI: only "Introduced", "House Draft N", "Senate Draft N" and "Conference Draft N", plus at most a handful of others; no "GM…" names.
* **`quality_check.py --structural ms` and `--structural hi`** at core `0f3c24c9`:

| | Versions with no stage (limit 5.5%) | Unmatched sponsors (limit 4.7%) |
|---|---|---|
| MS | about 0.0% (before: 61.4%) | about 1.4%, 110 left (before: 16.9%) |
| HI | about 0.01%, 1 left (before: 100%) | about 1.2%, 396 left (before: 6.5%) |

* **What's left unmatched, and is expected:**
    * MS: nominations whose author is GOVERNOR, LT. GOVERNOR and similar;
    * HI: Reps. Aquino and Ward, on 2025 bills carried over into 2026. That is a separate question for Ramon.
* **Fail** = any of these off. Stop and report.
* I check the same on the Mac replica, then record it on OPEN-669 and OPEN-668.

## Step 5: recompute dry runs (on a GO, after step 1; Mississippi's and Hawaii's after their re-imports have loaded and I've posted "verified")
For each run:
* Prove the rule is present in the core you run (`openstates/ddp_states/<st>.py` exists).
* Export the state's stored comparisons as the backup.
* Run `os-text-extract recompute-diff-order <st> --dry-run --list <file>`, and report the exact summary lines and the list's md5.

The three dry runs:
* **Missouri:** the ranges in `c639029` stand: `not_a_version` 700–800 and `corrected` 420–510; stop and report on anything outside them or any error.
* **Mississippi:** measured on the pre-fix data, about 1,118 papers become not-a-version and about 356 comparisons are corrected. The re-import changes the starting point, so **I'll post the ranges after measuring the re-imported data on the Mac replica.** Don't run it before that note.
* **Hawaii (report only):** no request asks for a Hawaii commit. Run the dry run after its re-import so we can see whether one is needed.

**No commit for any state** until Ramon's second go after he has seen the numbers. This is his rule from `fe2bb48`.

## If it goes wrong
* **Rollback:**
    * register the previous scrapers revision (rev 86 / v84);
    * re-tag the api-v3 and ddp-sync rollback images.
* A failed re-import leaves the state's earlier data in place until its load runs.

## Not authorized
* Any step before its GO note.
* Any recompute commit.
* Any other state's re-import or recompute.
* A second run of any re-import.
* Adding any host to `TLS_VERIFY_EXCEPTIONS`, or any setting that turns certificate checks off.
* Any manifest, schedule, routing or LegBot change.

Tickets: OPEN-668, OPEN-669, OPEN-671 (OPEN-146); fixes OPEN-804, OPEN-805, OPEN-806, OPEN-807, OPEN-808; OPEN-800 and OPEN-803.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
