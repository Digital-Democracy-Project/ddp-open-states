# REQUEST: OPEN-397, run North Carolina once on the new image (v36, revision 39) and verify. **Authorized by Ramon: do all of it now.** (Mac side, 2026-10-18 EDT)

**STATUS:** Ramon asked (Mac session, 2026-10-18) to hand this run to you. One state (NC), one run, then verify and report. A failed gate or an unexpected result is not permission to improvise: stop and report.

Jira: **OPEN-397** (Done on the code side). Code: openstates-scrapers fork PR #67, merged as `2692dde3`; the rule is recorded in ddp-open-states PR #278.

## 0. Why

NC's last scheduled run (2026-10-17, evening EDT, run id `nc-4ad2eace2886`) failed in `cloud_loader.py` with a `DuplicateItemError` ("Motion 8 To Adopt on SR 1 ... already imported", sources `.../2025/S/1` vs `.../2025E1/S/1`), exit 1 after 3558 s. Cause: NC's scraper keyed each vote by its roll-call number (`[S]-1`), which restarts every session, and the importer matches a vote with a `dedupe_key` on that key alone. The new extra session `2025E1` collided with the regular session `2025`. The whole import runs in one transaction, so **that run imported nothing**.

The fix: every NC session except `2025` now puts the session in the key (`2025E1-[S]-1`); `2025` keeps its bare keys so the 774 stored votes keep their ids (the broker keys Motions on those ids). Ramon ran `deploy-scrapers-image.sh` today: **`ddp-scrapers:v36`**, digest `sha256:c9ed7174dd833fed6f5e5aa43e3a5fbaeb38a64edf787c91fdfb8f0433668630`, **task-definition revision 39** registered (previous image v35). The v36 image was checked on the Mac: `vote_dedupe_key` is in `/opt/openstates-scrapers/scrapers/nc/bills.py` and `ve.dedupe_key = vote_dedupe_key(bill.legislative_session, rcs)`.

**Do not re-run the loader on `nc-4ad2eace2886`.** Its collected files carry the old keys, so it would fail the same way. The fix applies only to a **new collection**.

**No watermark work is needed.** NC's scraper ignores `start=` (OPEN-321): it walks every bill of every active session on every run, so a normal run collects everything, including the October extra-session bills. Do not delete or edit any marker in `ddp-openstates-scraper-memory`.

## 1. Gates (read-only; do first)

1. **G1 (image).** Confirm revision 39 is the latest ACTIVE `ddp-scrapers` revision and points at v36 with the digest above. If not, stop and report.
2. **G2 (baselines on RDS, read-only).** Report these before the run:
```sql
SELECT s.identifier AS session, s.classification, count(v.id) AS votes, count(DISTINCT v.dedupe_key) AS keys,
       md5(string_agg(v.id, ',' ORDER BY v.id)) AS id_hash
FROM opencivicdata_legislativesession s
JOIN opencivicdata_jurisdiction j ON j.id = s.jurisdiction_id
LEFT JOIN opencivicdata_voteevent v ON v.legislative_session_id = s.id
WHERE j.name = 'North Carolina' AND s.identifier IN ('2025', '2025E1')
GROUP BY 1, 2 ORDER BY 1;
```
Expected on the Mac's replica copy: `2025` = 774 votes, 774 keys; `2025E1` = 0 votes. Report RDS's own numbers and `id_hash` (that hash is the "before" for the 2025 vote ids). If `2025E1` already has votes, stop and report.
3. **G3 (quiet).** Check no NC scrape, archive or text-extract is running, and that nothing else will start for NC during the run (NC's weekly archive is Thursday). Also record the RDS latest restorable time.

## 2. The run

Run NC **once**, through the normal cloud path (Fargate collection with the latest revision, then `cloud_loader.py` into RDS), with **no session argument** and no other state. How to start it is your call: the manual trigger in the ddp-sync checkout the Mac side read accepts only `va`, `mi`, `ma`, `ut`, `az` and the batch targets (not `nc`, and `secondary` would run MI and others too, so do not use it); NC's own scheduled run or a direct `aws ecs run-task` plus the loader as was done on 2026-07-29/30 are the options. If you need a code change to trigger NC (for example adding `nc` to that list in ddp-sync), report it instead of making it. Watch for the completion record; expect NC's full walk to take about an hour.

## 3. Verify and report (a `reply-open397-nc-rerun-...` note)

1. The run id, the Fargate task's image (must be v36 / revision 39), and the loader's final result: **no `DuplicateItemError`**, completion `status: ok`.
2. The G2 query again. Expected: `2025` still **774 votes, 774 keys, same `id_hash`** (the regular session closed 2026-07-01, so no genuinely new votes are expected; if the count or hash moved, say so and show the difference); `2025E1` **greater than 0 votes**, and
```sql
SELECT count(*) FROM opencivicdata_voteevent v
JOIN opencivicdata_legislativesession s ON s.id = v.legislative_session_id
JOIN opencivicdata_jurisdiction j ON j.id = s.jurisdiction_id
WHERE j.name = 'North Carolina' AND s.identifier = '2025E1' AND v.dedupe_key NOT LIKE '2025E1-%';
```
must be **0**.
3. Anything the scheduler started as a side effect of the load (LegBot dispatch, bill-artifact generation, archive, embedding). Do not start any yourself, and do not stop one; just report what started. (OPEN-390's NC first-time changelog batch, about 3,550 versions, has to be ordered with the other LegBot batches and must not run alongside another, so Ramon wants to know if one starts.)
4. What you could not check.

If the run or the load fails, or any expected number differs: stop and report with the log tail; no retry and no rollback without authorization.

## 4. Not authorized

Any other state; editing or deleting any S3 marker, memory object or working-tier object (including run `nc-4ad2eace2886`'s files); re-running the loader on an old run; `--allow_duplicates`; changes to the task definition (rollback is `aws ecs deregister-task-definition --region us-east-1 --task-definition ddp-scrapers:39`, only with Ramon's say-so), flags, schedules, ddp-sync config or code; starting any archive, embedding, LegBot or bill-artifact run; touching the broker's data.
