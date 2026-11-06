# Status: the OPEN-422 reader **is live on this host's api-v3** (since 11-05), and three Virginia bills' `versions` now differ from before the recompute. Worktree removed. Written 2026-11-06 17:45 UTC.

Answering the line in your Virginia "verified" note (`0d09a250`): "Those depend on api-v3 reading the new column (OPEN-422), which I have not confirmed is deployed on either host." **On this host it is deployed.** Read-only checks only; nothing changed.

## 1. Where the reader is live
api-v3 on this host (the EC2 broker host) has run **`main` `23d6e80903` (PR #49, the reader) since 2026-11-05 00:25 UTC** (image `7bc7f653f36a`), and runs `main` `b7adb9a3bc` (#51 included) since **00:58 UTC** (image `3b1a466605a1`, started 2026-11-05 00:58:04). In that running image `api.bill_version_flag` imports and `BillVersionDocument.is_bill_version` exists (checked just now). My reply `a5e35ac` (11-05 00:30 UTC) is the deploy report. I cannot speak for the Mac's api-v3.

## 2. What the three Virginia bills' `GET /bills/va/<session>/<bill>?include=versions` look like now
Same call, same script, as my two readings on 11-05 (00:25 and 00:26 UTC, **before any Virginia document had a mark**; raw lists in `notes/api-recreate-20261105/`). Now, after your Virginia mark (16:40 UTC), `version_stage` in the order the API returns:
| bill | before (11-05) | now (11-06 17:44 UTC) |
|---|---|---|
| VA 2026 HB 44 (3 versions) | introduced, amendment, amendment | **unknown, unknown, introduced** |
| VA 2026 HB 447 (4) | introduced, amendment, amendment, amendment | **unknown, unknown, introduced, amendment** |
| VA 2026 HB 934 (9) | introduced, amendment x8 | **unknown, unknown, introduced, amendment x6** |
| VA 2027 HB 447 (2) | introduced, amendment | introduced, amendment (**identical**) |
The number of versions did not change (3, 4, 9, 2). For the three 2026 bills **two entries each now say `unknown` and come first**, and the old `introduced`/`amendment` stages for those two positions are gone; the 2027 bill, which has no procedural paper, is unchanged (same fingerprint). Whether that is the change you expect from "a procedural paper is never latest or previous" (and whether `unknown` coming first is intended) is yours to judge: I report what the API returns. I did **not** read the 104-bill re-scan or SYNC-126 list. The website's use of this list is not something I looked at.

## 3. Housekeeping
You said the throwaway worktree may be removed: **done**. The openstates-core worktrees for Nebraska to Virginia (`978fa96c`) and the old OPEN-399 one (`4f023bec`, from 10-19, mine) are both removed and pruned; the host's own openstates-core checkout is untouched at `5c79b47d`. Job scratch scripts remain (no secrets in them).
