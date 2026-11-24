# UPDATE (not a GO) to `de80ea4` and `a92378e`: the core rollout moves from `0f3c24c9` to **`eb197d74` or newer** (adds OPEN-809). It is **one** rollout: api-v3 on both hosts and EC2 ddp-sync, done **before any run on v85**. Then v85 is built at that core. The Hawaii re-import now also fixes the Aquino/Ward sponsors. 2026-11-24 (Mac side, Onboard New States)

**Not a GO.** Every step still waits on Ramon's go. Everything else in `de80ea4` and `a92378e` stands: Utah canary first, MS/HI/ME re-imports, recompute dry runs only, "Not authorized". Only the core commit and the order change.

## What changed
* **Core main is `eb197d7407253550912fc8ba9f9b0aa0c9da127f`** (#147, OPEN-809, merged by the PM session).
    * Since `0f3c24c9`, the only change is `openstates/importers/bills.py` plus a test file. **No migration.**
    * **What it does:** when a sponsor matches nobody in the session, and the bill's first action is before the session start, core tries again with the members seated on that day. This reuses OPEN-767's same-day rule. A sponsor that already matched is never re-decided.
    * **Measured on the Mac replica (806,930 stored sponsorships):** 0 lost and 0 switched in every state.
        * Gains: HI +396 (Aquino and Ward), VA +28, FL +7.
        * Those appear only when those bills are imported again.
* **Possibly one more:** OPEN-817 (a vote dated after its session ended also matches a member seated on that day). Its PR is being opened now.
    * **If it is merged before the rollout starts, use that newer core main instead.** I'll post an UPDATE naming the commit.
    * **Don't wait for it:** without it, only Maryland's 2 "Harlan" votes stay blank.
* Ramon lifted the core hold (via the PM, 11-24: "Now, + rebuild").

## The order now (each on a GO)
1. **One core rollout at `eb197d74` (or the newer main I name), as in `de80ea4` step 1:**
    * EC2 api-v3 (rollback tag, build, `up -d --no-deps api`);
    * EC2 ddp-sync;
    * the Mac api-v3 (`refresh-api-v3.sh`, which needs `SCRAPERS_IMAGE_CORE=<the new core>`; Ramon or me).
    * **EC2 ddp-sync:** if `/opt/ddp-sync` is still at `85c8888`, rebuild at `85c8888` with the new `DDP_CORE_SHA`. If you pull to `8653f08` (SYNC-188), also pass `DDP_SCRAPERS_SHA`: v85's scrapers commit, `ecd44eab…` or later, as in ddp-sync `132d8cf`.
    * Post the in-flight list first. Never 02:15–04:45 UTC; api-v3 not 05:00–07:00 UTC.
    * Then `check-core-pin-drift.py --image-core <new core>` exits 0 on every container.
2. **Image v85 (Ramon):** scrapers main **`ecd44eab` or later**, with **the same core as step 1**. Mac side checks `DDP_CORE_COMMIT`.
3. **The Utah canary on v85** (`3e6c766` step 3), before any other run on v85.
4. **Re-imports on v85, one heavy load at a time:**
    * **Hawaii first:** `hi?full=true&sessions=2026`.
    * Then Mississippi (`de80ea4` step 4).
    * Then Maine (`a92378e` M1–M3).
5. **Recompute dry runs** (`de80ea4` step 5, unchanged), at the step-1 core.

## Hawaii pass/fail, updated
* **Unmatched sponsors: expect about 0 (before: 2,160 / 33,134).**
    * 6.5% → 1.2% came from OPEN-805.
    * The 396 left (Aquino 234, WARD 161, Ward 1) now link through OPEN-809.
```sql
SELECT s.name, count(*) FILTER (WHERE s.person_id IS NULL), count(*)
FROM opencivicdata_billsponsorship s JOIN opencivicdata_bill b ON b.id=s.bill_id
JOIN opencivicdata_legislativesession ls ON ls.id=b.legislative_session_id
WHERE ls.jurisdiction_id='ocd-jurisdiction/country:us/state:hi/government' AND ls.identifier='2026'
  AND s.entity_type='person' AND upper(s.name) IN ('AQUINO','WARD')
GROUP BY 1;   -- expect 0 unmatched for each
```
* The versions check, the other sponsor checks and Stage 3 are as in `de80ea4`.

## Not authorized
Unchanged from `de80ea4` and `a92378e`. Also:
* a second core rollout once v85 is running, unless Ramon gives a new go;
* VA or FL re-imports for OPEN-809's gains (not requested).

Tickets: OPEN-809, OPEN-805, OPEN-668 (OPEN-146); OPEN-817 pending; SYNC-188.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
