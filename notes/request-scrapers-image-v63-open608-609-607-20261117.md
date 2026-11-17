# REQUEST (waits on Ramon's go): one scrapers image v63 with Oregon joint-committee voters (OPEN-608), Oregon "no votes yet" (OPEN-607 a) and the Massachusetts catch-up code (OPEN-609, dormant). 2026-11-17 (Mac side)

**Not a GO yet.** Ramon builds and registers the image with `deploy-scrapers-image.sh`. The prod agent's part (below) starts only after that and a GO note naming the revision.

**Ramon, 2026-11-17 (/catch-up pop-up):** "Merge MA first, then build (Recommended)". Both Massachusetts PRs are merged (PM session, 11-17): scrapers #119 → `92ac338c2`, ddp-open-states #403 → `6fc71337`.

## Correction to the premise: Alabama's fix is already live
The decision assumed this image must carry OPEN-569 (Alabama version dates) before Alabama's Sunday 11-22 scrape. **It doesn't need to: v62 = `ddp-scrapers:65` already carries both halves.**
* core #104 (`96445eb26`) is an ancestor of v62's core `44c3b8dc8`;
* scrapers #100 (`77c399b6b`) is an ancestor of scrapers #109 (`93aee7494`, and of #109's own branch head). v62 was built after #109 (`go-us-flip-open542-v62-20261117.md`: "carries scrapers #109").

So Sunday 11-22's Alabama run on revision 65 already uses the date ordering. OPEN-569's data steps (archive, `recompute-diff-order al`, `remove-stale-documents al`, final 0/0 dry run) can follow that run without this image. They will be requested separately, with gates, after it. **This image has no hard deadline.** Oregon is the reason to register it before Oregon's next run.

## What v63 carries (main since v62)
| Repo | Commit | Change | Effect |
|---|---|---|---|
| openstates-core | `b5728c43` (#116, OPEN-608) | A vote held by the whole legislature looks up voters among House, Senate and legislature members | Oregon's 931 joint-committee member votes link (Mac replica: 0 → 931 of 931); Nebraska unchanged (85,456 same people, 0 differ) |
| openstates-scrapers | `0e587f750` (#118, OPEN-607 a) | Oregon's votes scraper reports "no votes yet" instead of failing when Oregon has no roll calls | A new Oregon session with no votes doesn't fail the run |
| openstates-scrapers | `92ac338c2` (#119, OPEN-609) | Massachusetts catch-up selection (journals, new-bill list, Session Laws, hearings; 28-day full walk) | **None until `ma.scrape.start_filter: true`**, a separate PR on Ramon's go; MA keeps full runs |
| ddp-open-states | `6fc71337` (#403, OPEN-609) | `cloud_collector.py` carries the scraper's catch-up record between Fargate runs, saved last | Optional: a missing or unreadable record means a full run |

* **No core database migration** since v62 (checked: `git diff --name-only 44c3b8dc8 b5728c43` shows none).
* **Core drift closes:** EC2 api-v3 already runs core `b5728c43` (accepted gap, `be6f951`). With v63 on the same core, `check-core-pin-drift.py` should pass with no disagreement on EC2, and no api-v3 rebuild is needed there. The Mac api-v3's core was not read here; check it in step 2.
* **Not in it:** OPEN-544's core cleanup (not built).

## Rules
* No release during a running scrape of a state the image changes (or, ma, ne). PA's nightly (04:00) and WA's (02:30) are unaffected, but don't register mid-run of anything (ECS check as usual).
* At most two state pipelines at once.
* A stop is harmless: report it, don't retry past a gate.

## Prod agent, after Ramon registers v63 and posts the GO
1. **Check:** the latest active `ddp-scrapers` revision runs v63; its `DDP_CORE_COMMIT` is `b5728c43`; the image's `or/votes.py` has the EmptyScrape change, and `ma/catchup.py` exists.
2. **Drift:** `check-core-pin-drift.py --image-core b5728c4326fea4bdc33b721738ecdbe5ac4d8b02 --container ddp-openstates-api-1` on EC2. **Gate:** exit 0. Report the Mac api-v3 result too, if you can read it.
3. **One Oregon run** on v63 (one POST, no retry), only on Ramon's go in the GO note. Report status, failed, bills and vote events.
4. Then the Mac side rechecks on the replica: Oregon joint-committee member votes **931 of 931 linked**, and Oregon's unlinked share drops below 4.7% (from 4.75%).
5. **Massachusetts:** nothing to do. Its next run on v63 should look like the last one (a full run, about 10–14 h). Report if it doesn't.

## Not authorized
Any manifest change (MA's `start_filter` included), task-definition change beyond registering v63, broker, ddp-sync or api-v3 deploys, and any Alabama data pass.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
