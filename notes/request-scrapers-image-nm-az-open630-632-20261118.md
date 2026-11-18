# REQUEST (waits on Ramon's go): new scrapers image with New Mexico's pandas fix (OPEN-630) and Arizona's 2027 session (OPEN-632), then rerun NM and AZ. Before Sunday 11-22 02:00 UTC. 2026-11-18 (Mac side)

**Why:** two states fail in the first minute on revision 68 (v65), and nothing loads:
* **New Mexico** (OPEN-618, your `4a6fd1d`): the votes scraper needs pandas.
* **Arizona** (your `5630d1a`): azleg lists the 2027 session, and the scraper refuses to run.

Ramon, 2026-11-18 (/ask-me): "Fix it, one image for both". Both fixes are merged:

| Fix | PR | Merge commit |
|---|---|---|
| pandas in `requirements-openstates.txt` and in the image's import check (OPEN-630) | ddp-open-states #419 | `9cad87e` |
| AZ 2027 session, active from 2027-01-11, 2026 until then (OPEN-632) | openstates-scrapers #133 | `4686b774` |

**Also in this image, no behaviour change** (built from main; reviewed and merged by the PM session):
* OPEN-555 steps 1-2: per-state values read from `jurisdictions.yaml`, each falling back to today's constant. core #128 and scrapers #132, ddp-open-states #423; the image carries `/app/jurisdictions.yaml`.
* OPEN-544: `reverse-action-order` reads no manifest label (core #129).
* **Core moves from `46cc5759` to `94082df`.** I diffed them: 5 files, **no migration, no model change** (`ddp_manifest.py`, `resilience_profiles.py`, `text_extract.py` and tests). So api-v3 needs no rebuild for this image; `check-core-pin-drift.py` will report the expected gap (api-v3 at `46cc5759`).

## Part A, on the Mac (not yours)
1. Ramon runs `CONFIRM=1 bash deploy-scrapers-image.sh` in a real terminal: build, the in-image checks, push. The import check now includes pandas.
2. If the confirm prompt stops at registering, I register the new revision myself (Ramon's standing permission: "the agent has my permission to register the image himself").
3. I post the new tag and revision here as a `reply-` note before you start Part B.

## What I need from you (Part B, after my reply note names the revision)
1. **Gates, read-only:**
   * the ddp-scrapers family's latest ACTIVE revision is the one my note names, and its image is the new tag;
   * `python3 check-core-pin-drift.py --image <tag>` reports image core `94082df`; report the api-v3 gap as expected, not a stop;
   * no `nm` or `az` run in flight.
2. **New Mexico:** `POST /ddp-sync/v1/trigger/openstates-scrape/nm`, one call, no retry. Gates as in ddp-sync `go-open618-nm-first-scrape-v65-20261118.md`:
   * the new revision;
   * the active-sessions line (report it);
   * vote events > 0;
   * `status=completed failed=0`;
   * the archive finished: report fetched and `fetch_errors`.

   Report the run id, bills, vote events and archived documents.
3. **Arizona,** after NM finishes: `POST /ddp-sync/v1/trigger/openstates-scrape/az`, one call, no retry.
   * **Gates:** the new revision; no session-list error; the active session reported as `57th-2nd-regular` only; `status=completed failed=0`; the archive finished.
   * Report the run id and counts.
4. Hand back with a `reply-` note. The Mac side then checks NM's action order (OPEN-620) and the Stage 3 gates on the replica.

## Stop conditions
* A different revision or tag.
* Core not `94082df`.
* A failed run: report it, don't retry.
* A session-list error.
* Any write outside `nm` and `az`.

## Not authorized
* LegBot for NM.
* Any manifest edit by hand.
* Any other state's manual run (scheduled runs carry on as usual on the new revision).
* An api-v3 rebuild.
* `recompute-diff-order`, relabels, or OPEN-628's vote-order backfill (that has its own request, `094331c`).

## Timing (real reasons only)
* Before Sunday 11-22 02:00 UTC, when NM joins the weekly batch.
* Not while an `nm` or `az` run holds its lock (the trigger answers 409).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
