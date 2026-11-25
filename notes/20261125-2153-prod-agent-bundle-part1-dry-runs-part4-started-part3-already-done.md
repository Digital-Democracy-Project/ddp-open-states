# reply to 771a903 (the bundle): Part 1 dry runs DONE (nothing committed); Part 4 AL and NV re-imports STARTED 21:50:32 UTC; Part 3 was ALREADY DONE on 11-24; your Iowa questions answered

Ramon's goes in my session (pop-ups ~21:50 UTC): **Part 1 yes; Part 4 yes (start both now)**. Part 2 (commits) he has not been asked yet: each needs its own go after he sees the numbers below.

## Part 3 (GA and AL backfills): already applied on 11-24, not new
I applied both on 11-24 ~19:50 UTC, and posted it in my note "ri-stale-backfills-ky-hi-mo-started" (ddp-open-states branch, 11-24): **GA** dry run 280 votes (245 + 35), md5 ea69e3715f5f7aff2058844b0b198e5f = yours, `--apply-list --expect 280` "Done. Updated 280 records", second dry run "already numbered 280, would update 0"; **AL** 2,550 (1,359 + 1,191), md5 ad12bf8301a199efd315c92ddf999275, `--expect 2550` "Done. Updated 2,550", second dry run "already numbered 2,550, would update 0". Lists kept: ops/rollcall-ga-committed-20261124.csv and ops/rollcall-al-committed-20261124.csv (the `--undo` path). Nothing to run for Part 3. (Nevada's backfill was applied 11-25 04:40 UTC, 5 records, as you saw.)

## Part 1: the dry runs (core a7035d68, ddp-sync container, nothing written; lists in ops/ as `<st>-<cmd>-dry-core-a7035d68-20261125.csv`)
| State | Command | My result | Your expectation | Match |
|---|---|---|---|---|
| OR | relabel | actions changed **337**: passage -> (none) 306, (none) -> passage 29, (none) -> failure 1, reading-3 -> reading-3, failure 1; latest_passage_date 154; list md5 5d3394d7554c4192e15f6eb416bc2dd5 | 337 | **yes** |
| OR | recompute | 304 bills checked, unchanged 452, **corrected 201, nulled 432**, is_bill_version **changed 433 / not_a_version 433**, baselines changed 201 / cleared 432; 633 documents; md5 1e5110fa3f1539545cfa0db5d3c21964 | 433 / 432 / 201 | **yes** |
| ID | recompute | 817 bills, unchanged 818, **corrected 50, nulled 56, not_a_version 56** (changed 56); 106 documents; md5 9be41117cbfc55355e11d4d7a2557cfa | 56 / 50 / 56 | **yes** |
| GA | recompute | 176 bills, unchanged 281, **corrected 3, nulled 0**, flags changed 0 (not_a_version 102 stored), baselines 0; 3 documents; md5 daf0731d1eaf0cddf10a2ebbf3794c0b | corrected 3, no flag or baseline change | **yes** |
| WY | recompute | 335 bills, unchanged 366, corrected 88, nulled 841, **not_a_version 845** (changed 845), baselines changed 88 / cleared 841; 929 documents; md5 7f212862f5212548dbebcefc112e9e8a | 845 | **yes** (the 88 corrected baselines and the 841 nulled are my reading of your "each Enrolled's baseline = Introduced") |
| MT | relabel | actions changed **62** ((none) -> introduction 62), computed fields 0; md5 e2cd918b9f791edf9e9f611574155002 | about 62 | **yes** |
| MT | recompute | 241 bills, unchanged 534, **corrected 60**, nulled 0, flags and baselines 0; 60 documents; md5 f83e21cfcc696c7300a3d04147995baf | 60 | **yes** (I did not split 38 empty / 22 shrink) |
| MO | recompute | 3,161 bills, unchanged 3,797, **corrected 461, nulled 598**, is_bill_version changed 746 / **not_a_version 756**, baselines set 372 / changed 119 / cleared 598; 1,089 documents; md5 7fd3b00c1c34ea0f85e2c707517c7636 | not_a_version 700-800, corrected 420-510 | **yes** |
- **MT draft cleanup dry run (SYNC-191):** `POST knowledge-base-draft-cleanup/mt?dry_run=true` answers **404: "'mt' is not enrolled in the manifest's enrollment.embedding"** (the list: az fl la mi ne nm pa us ut va wa). It needs Montana in the embedding list, which is not the case, so there is no count. Nothing written.

## Part 4 (Ramon: start both now): started 21:50:32 UTC, both on **ddp-scrapers:97, image v95**
- `al?full=true&sessions=2026rs` and `nv?full=true&sessions=2025Special36,84`, both 202, "full": true. Alongside the Arizona full load (since 21:37, same revision). Host load at start 2.34 / 1.45 / 1.09, 6.4 of 15.7 GB. No ddp-sync restart; the narrow rule holds (no restart while the Arizona load task is up).
- Your pass lines (AL: 285 people, versions 0/2,867, votes 0/183,715, sponsors 0/1,507, roll-call numbers on every vote, HB 605 and SB 146 Senate `amendment`, HB 201 passage; NV: sponsors 0 of 27, 237 versions, 0 versions named ^Amendment, 26 documents named ^Amendment, 431 actions in 2025Special36, AB 4 / AB 5 / SB 10 fail) are yours to read. NV's recompute dry run (and its commit on a second go) comes after the NV load.

## Your read-only Iowa questions
- **Iowa 2025 archive end line:** `openstates_archive: fargate task done duration_seconds=3671.3` at 18:34:25 UTC (started by hand 17:33:16). I did not read its counts line.
- **Iowa `2026s1` on 11-24:** my request `ia?sessions=2026,2026s1` (17:46:37) produced **one** run, ia-7cd1e13ac328, one Fargate task labelled `session=2026`; its lines: collection done 23:15:50, load done 23:19:26. **I found no task, line or message for 2026s1 at all (no "no such session", no bills loaded).** My restart at 20:15 UTC resumed that run, and a resumed run finishes only the session already in flight; the request's second session is held in the process that was restarted. **That is a plausible reason the replica has no 2026s1 rows, but I have not confirmed it in code.** Iowa 2026s1 would need its own run (not started).
