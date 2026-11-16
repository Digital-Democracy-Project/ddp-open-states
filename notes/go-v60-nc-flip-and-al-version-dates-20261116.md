# GO: image v60 is LIVE as `ddp-scrapers:63`. North Carolina's flip now (before NC's first scrape on v60), and Alabama's version-date passes after Alabama's Sunday scrape; each saved only if its dry run matches the gate. 2026-11-16 05:00 UTC (Mac side)

**Ramon's go:**
* 2026-11-16 ~04:45 UTC: he ran `deploy-scrapers-image.sh`, and "can you register the new image once it's done?". The script registered it.
* OPEN-543: "Fix before launch" (pop-up 11-16).
* The data passes: "Save if the trial matches" (11-16, `9963ec8`). Each step below commits on its own **only if** its dry run passes its gate. Anything else stops and you report.

**Step 7 (struck words) and step 8 (api-v3 #61) of `9963ec8` are still yours, as before.** Please post their results when done. Your last note was `3b41db3`, with step 7's dry runs running.

## v60 = `ddp-scrapers:63` (live 04:57 UTC; v59 = revision 62)
* **Digest:** `sha256:c4eee8ab2fcb83717a274de430d424a2cc918aaf286d691cf2a48353eb83126a`.
* **The script's checks:** imports, plus one Utah bill (RC 0).
* **My smoke test inside v60:** `os-text-extract` starts; `reverse-action-order` and `remove-stale-documents` print their usage; core has Alabama's date-first ordering; the scrapers carry the NC time fix and PA's incremental export.
* **New in v60:**
  * **NC:** actions oldest first (#102), all roll calls (#104, about +719), motion rules (#103), vote times (#105), two-word names (#101);
  * **AL:** version dates and adopted substitutes only (core #104, scrapers #100);
  * **PA:** incremental nightly from the legislature's daily Bill History export (#106; ddp-open-states #381 sets `start_filter: true`).
* **Rollback (Ramon):** `aws ecs deregister-task-definition --region us-east-1 --task-definition ddp-scrapers:63`.

## A. North Carolina flip (now, before NC's first v60 scrape on Sunday 11-22 02:00 UTC). Do not trigger NC before it.
1. **Hold:** nothing to change. NC runs only on its Sunday job. **Do not trigger NC** until A.4 is done.
2. **Flip:** `os-text-extract reverse-action-order nc --manifest /opt/ddp-open-states/jurisdictions.yaml --dry-run`. The checkout's list has `nc` `true`; **no** override. Use core main (`96445eb26` or later, the core in v60).
   * **Gate:** `reversed` between **2,320 and 2,360** (Mac replica: `reversed=2343 actions=20035`; dates 2,327 newest first, 16 single-day) and 0 errors.
   * Then `--commit --expect <dry-run count> --list <lasting path>`.
   * Then a second dry run must show `reversed=0`.
3. **Label:** ddp-open-states **#380** sets nc `newest_first: false`. **Ramon merges it.** Then pull and run `rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync`. **Gate:** `/ddp/enrollment` shows `newest_first` true for **us only**. If #380 isn't merged when the flip is done, post a status note and wait: the label must follow the flip, and NC must not scrape before both.
4. No broker bill-event task is scheduled (`49ee4fb`), so there is nothing to re-bootstrap.

## B. Alabama version dates (OPEN-569), after Alabama's Sunday 11-22 run on v60 has finished its import **and archive**
Measured offline by the builder. Each step commits only on its gate:
1. **Check first:** 0 Alabama versions without a date; HB 315's versions in the order Introduced → Tillman substitute (03-17) → Engrossed (03-17) → Senate committee substitute (04-02) → Enrolled (04-08).
2. `recompute-diff-order al --dry-run`. **Gate:** `corrected` ≤ 5, and `nulled` about **1,116 (±1%)** (the old undated copies). Commit.
3. `remove-stale-documents al --dry-run`. **Gate:** `stale` about 2,923, `removed` about 2,867 and `kept_last_copy` about 56 (±1%), with `kept_no_file_hash=0`. Commit with `--expect` and `--list`, with a full-row export taken first as on 11-16.
4. A final `recompute-diff-order al --dry-run`. **Gate:** `corrected=0 nulled=0`.

**The `b261ead` hold on `recompute-diff-order al` ends only through these gates.**

## C. Reports owed (nightly note)
* **PA's first v60 nightly (04:00 UTC 11-17):**
  * the log line `PA OPEN-574: export … lists 5286 bills, N changed since …`;
  * no `doing a full walk` warning;
  * `mode=incremental`;
  * the run time (expected minutes, not hours).

  If it does a full walk, quote the reason line.
* **SYNC-162's first LegBot trigger** (owed from `e3de068`).

## Not authorized
* Triggering NC or AL scrapes.
* `--even-if-manifest-says-oldest-first`; any us action.
* Any commit whose gate fails.
* The broker deploy (separate, `eac07011`).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
