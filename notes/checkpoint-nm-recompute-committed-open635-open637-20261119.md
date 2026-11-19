# CHECKPOINT: NM recompute-diff-order COMMITTED (OPEN-635 + OPEN-637), second dry run clean

Written 05:17 UTC 11-19 (date -u at write time), from the production EC2 host. **The user's words in session:** "GO for New Mexico ;-)" (a direct go for the commit, after I had reported the dry run in 47e3abd, including that it clears 85 by design).

## Before the commit (05:16 to 05:17 UTC)
- Gates: no NM task in ECS (the only running task was pa on revision 71), no NM line in the ddp-sync log; core c983ae68 (throwaway worktree), api-v3 at c983ae68.
- **Fresh backup** /home/bitnami/ops/step-open635-637/nm-before-commit.csv: md5 **51da907a6cff393d6482c03349a18307**, identical to the first backup nm-before.csv (nothing had moved).
- **Repeat dry run:** corrected=129 nulled=85, is_bill_version changed=85, diff_baseline_id set=129 cleared=85; list md5 **aa8f03e964de4348328a4c7a444905ba**, identical to the first. (This command has no --expect in full mode, so an identical repeat was my guard.)

## Commit (05:17:23 to 05:17:28 UTC, 5 s, exit 0, 0 errors)
`os-text-extract recompute-diff-order nm --commit` (host venv, core c983ae68):
- `nm: [COMMITTED] 812 bills checked | unchanged=899 corrected=129 nulled=85`
- `nm: [COMMITTED] is_bill_version: set=0 changed=85 not_a_version=85`
- `nm: [COMMITTED] diff_baseline_id: set=129 changed=0 cleared=85`
Output: /home/bitnami/ops/step-open635-637/nm-commit-raw.txt. Only NM was touched.

## After
- **Second dry run: `unchanged=1113 corrected=0 nulled=0`, is_bill_version changed=0 (not_a_version=85), diff_baseline_id set=0 changed=0 cleared=0; change list 0 documents.**
- Counts read from RDS: NM documents **1,113**; with a comparison **215** (= 171 + 129 - 85, as your table says); **85 not a version**; 812 bills; Final Versions with a baseline **129**; Amendments in Context documents cleared and not a version **85**.
- The tool did not ask for a search-index refresh. I did not run one (needs a GO). No LegBot, no other state.

**Rollback if ever asked:** the backup holds each document's old is_bill_version, diff_baseline_id and diff text; restoring means a reviewed write from nm-before-commit.csv.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
