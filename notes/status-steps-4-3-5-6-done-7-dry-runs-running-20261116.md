# Status: steps 4.3, 5 and 6 DONE and checked; step 7 dry runs RUNNING; step 8 not started. 2026-11-16 02:56 UTC (prod agent)

Answers `b261eadb` (skip 4.2, continue 4.3, 5, 6, 7, 8) and `2f57a434`. User's words in session (pop-up earlier tonight): **"Run each step if its dry run passes its gate"**. Every gate passed; nothing failed. All data steps ran with **core `eec94082b` (a throwaway worktree on `PYTHONPATH`) on the host venv, Python 3.9.2**, not v59 (3.13), except 4.3 (container tool, below).

## 4.3 Alabama people load: DONE
- Pulled `people` checkout `/opt/ddp-open-states/people` to main **`eae05f197d`** (fast-forward, 2 files, PR #21), clean.
- **The host's `os-people` is the wrong tool again:** its `--safe` run printed exactly the two updates and the missing person but exited 1 (the same refusal as 11-12). I used **the container's `/opt/venv-openstates/bin/os-people`** (what the weekly job uses; `OS_PEOPLE_DIRECTORY=/opt/ddp-open-states/people` set, `DATABASE_URL` resolved live inside the container).
- **Safe run (02:44:03):** `processed 299 person files, 0 created, 2 updated`: the two Alabama files **Brock-Colvin** and **Greg-Barnes**, and `1 went missing from source data, left in database unchanged: ocd-person/76f9d6ad-...: Mack Butler` (the same person as on 11-12). Its exit code was 1 in safe mode.
- **Real run 02:44:28 to 02:44:38, rc 0:** the same lines (`0 created, 2 updated`, Mack Butler left unchanged). **Gate met** (only the two `other_names` additions). Read after: `William Brock Colvin` under Brock Colvin and `Gregory Barnes` under Greg Barnes exist in `opencivicdata_personname`.

## 5 Pennsylvania recompute: DONE (before the 04:00 nightly)
- Dry run 02:44:56-02:45:22: `pa: [DRY RUN] 5286 bills checked | unchanged=12393 corrected=12 nulled=0`, `is_bill_version: set=0 changed=0 not_a_version=0`. **Gate met** (`nulled=0`, corrected 12 inside 8-16).
- **Export first** (restore path): `/home/bitnami/ops/step5-pa-20261116/pa_diffs_before.csv`, **12,405 rows**, 18,896,788 bytes, md5 `990cfe9df084648023aa6cf9615b972c`, mode 600; same format as the Massachusetts export (NULL = empty field, non-NULL = text prefixed with one \x01).
- **Commit 02:45:40-02:46:04:** `corrected=12 nulled=0`, same as the dry run. **Second dry run: `corrected=0 nulled=0`.** Nothing ran for PA at the time (0 ddp-sync lines, 0 tasks).

## 6 Louisiana, then Nebraska flip: DONE
- Checkout `dead3de7` (la and ne `newest_first: true`), `--manifest /opt/ddp-open-states/jurisdictions.yaml`, no `--even-if-manifest-says-oldest-first`. 0 la/ne ddp-sync activity before each commit.
- **LA** dry run 02:46:49-54: `reversed=2609 actions=30431 skipped_single_action=7`; `stored dates: mixed=94 newest_first=2496 same_day=19`. **Gate met** (2,560-2,620; no error line). **Commit** `--commit --expect 2609 --list ...` 02:47:09-37: same numbers; `latest action fields recomputed and changed: 1093`. **Second dry run: `reversed=0 skipped_already_reversed=2609 skipped_single_action=7`.**
- **NE** dry run 02:47:47-51: `reversed=1847 actions=18208`; `stored dates: newest_first=1845 same_day=2`. **Gate met** (1,820-1,850). **Commit** `--expect 1847` 02:48:04-21: same; `latest action fields recomputed and changed: 570`. **Second dry run: `reversed=0 skipped_already_reversed=1847`.**
- **Change lists (old and new order per bill):** `/home/bitnami/ops/step6-flip-20261116/la_flip_committed_list.csv` (2,609 rows) and `ne_flip_committed_list.csv` (1,847 rows), plus the dry-run lists and raw outputs in the same folder. `--undo --commit` would work inside the hold; I have not used it.
- **6.4, after both committed:** `rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync --state la` 02:49:05-06, **exit 0**; it pulled **6 commits to `5f945b01`** (`origin/main`, as your update said; 3 files in the diff: PRIMITIVES, `jurisdictions.yaml` with only la/ne `true` to `false` plus comments, the validator test); drift `OK ... (13 jurisdictions)`; **md5 `a0436ed508d18e4bc29ab97bef02b2d1` in the checkout, api copy and container** (was `3502890e...`). **Gate: `/ddp/enrollment` 200, 13 states, `newest_first` true for exactly nc and us**, 0 `voatz` keys, PA bills 200, a PA bill page with versions 200, ddp-sync log 0 manifest errors.
- **6.5:** no scheduled broker bill-event task exists (`49ee4fb`), so nothing to re-bootstrap. **6.6:** the hold needed no mechanism (nothing is scheduled for la or ne before Sunday 11-22 02:00 UTC); I did not trigger them and will not.

## 7 Struck words (la, ne, wa): dry runs RUNNING
- Host venv with core `eec94082b` (PyMuPDF 1.26.5 and `pdftotext` present), the same route as Alabama's OPEN-530. One background script runs **la, ne, wa dry runs in that order**. **LA started 02:50 and was still running at 02:57 (about 35% CPU, no summary yet)**, so I have no number or ETA. No commit until each dry run meets your gate (stale count within +/-3% of LA 3,391, NE 1,691, WA 3,677, and 0 extraction errors). WA runs after LA and NE and well clear of WA's own nightly (02:30 tomorrow).

## 8 api-v3 to main (#61): NOT started
After step 7 (in order).

## Also in the queue, not mine to start
The ddp-sync release `df605d7` (`9862028`) and the broker deploy `c52e91d2` (`eac07011`, marked NOT CLEARED, needs your D1 and D2): neither has the user's go in this session, and the ddp-sync window ("before 02:55 UTC" has passed; "after PA's run has finished its LegBot step") is not open. I will ask the user.
