# REQUEST (not a GO): the next scrapers image after v78, for OPEN-766 (Wyoming end dates), OPEN-765 (North Carolina's 2025 end date) and OPEN-764 (Louisiana presiding officers). Scrapers main is `256259be`; core is unchanged at `7f531958`. 2026-11-22 (Mac side, State Specific Handling)

**Not a GO.** Ramon builds the image (`deploy-scrapers-image.sh`). v78 holds scrapers `f0ac9ef8` exactly (`e27e5b0`; correction `a540688`).

## What is new since v78 (scrapers main `256259be89d4e66600a4c703ea8a1569d34d867f`)
| Merge | What |
|---|---|
| #220 (OPEN-766, `c42e6df6`; Onboard New States) | Wyoming: six sessions end on their last working day (Ramon). **Wyoming's first scrape waits on this image** |
| #219 (OPEN-765, `a6fb5162`; this session) | North Carolina's 2025 session ends 2026-12-18, the sine die date of the legislature's Resolution 2026-6 (SJR 1091) §6, not 2026-07-01. With the old date, a member sworn in later (Sen. Jerry Tillett, 2026-09-03) is not matched to that session's votes |
| #221 (OPEN-764, `256259be`; Onboard New States) | Louisiana: "Mr. Speaker" and "Mr. President" on roll calls resolve to the session's presiding officer, read from the manifest field `la.votes.house_speaker_by_session` / `senate_president_by_session` (ddp-open-states #460, merged `c25b56a1`). Without the manifest value the title stays as printed (fail-safe) |

* No migration and no new setting.
* **Order for North Carolina:** after this image is live, OPEN-611's Tillett re-link (ddp-open-states #459, merged `bbfd8c16`; 5 votes) may run its dry run and, on Ramon's go, its commit. Committing before this image is live would be undone by the next NC import.
* **Louisiana:** the manifest the scrapers read must carry #460's values, or the officers stay unmatched (no harm, no effect).
* **Expected later:**
  * OPEN-767 (openstates-core, date-aware voter matching; still building);
  * BROKER-579 (#222, PA/NE/LA veto overrides, in review).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
