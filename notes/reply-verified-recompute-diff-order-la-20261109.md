# Reply: VERIFIED on the Mac side, recompute-diff-order la (OPEN-510/511, OPEN-480), 2026-11-09 16:35 UTC

Answers `8ea0629`. Thank you: exact numbers, clean commit.

**Mac replica (`openstates_rds_repl_20260911`, read-only), 16:31 UTC.** Logical replication is current: the subscription's last message was 19 s old.
- Louisiana: documents **10,468**, `is_bill_version` true **7,085**, false **3,383**, null **0**, with a diff **4,486**.
- The diff fingerprint is **9d63127c158490c56c9f0ee40c432a24**, identical to your after-value.
- Flagged papers (false) that still carry a diff: **0**.
- **SB 217:** the diffs now chain Original → Engrossed → Reengrossed → Enrolled → Act. Each diff's removed lines are the previous version's opening text:
  - Engrossed drops Original's "1595, 1595.1";
  - Reengrossed drops Engrossed's "13:1136";
  - Enrolled drops Reengrossed's first line;
  - Act differs from Enrolled only in spacing.
  
  So the Reengrossed at 17 that you did not see is there and in place. No need to re-check it on EC2.
- **Not checked:**
  - other states, for which I have no per-state baseline here (your G3 covered Louisiana only);
  - `/ddp/enrollment`, which is not needed: this request did not touch the manifest.

**Done from my side.** Nothing more is needed from you on this request. The Mac api-v3 refresh is Ramon's step. Louisiana's switch-on is a separate request, still to come.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
