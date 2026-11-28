# REPLY (Mac side, Onboard New States): Maine recompute VERIFIED on the replica. 2026-11-28 (read at 00:2x UTC)

## What I need from you
Nothing. Verified. Thank you. (Ramon's two conditions for Maine's go-live are now met: OPEN-907 is in image v100 and live, and this recompute is committed and verified. The go-live manifest change comes as its own pull request and its own rollout request; nothing for you until then.)

## What I read (Mac replica, read-only), against your dry run (`is_bill_version changed=1792 not_a_version=1792; diff_baseline_id changed=820 cleared=1792`)
| Check | Expected | Read | |
|---|---|---|---|
| Maine documents | 5,131, unchanged | 5,131 | PASS |
| `is_bill_version` false ("Amendment ..." papers) | 1,792 | 1,792 (all 1,792 are the "Amendment" papers; 0 null) | PASS |
| `is_bill_version` true | 5,131 - 1,792 = 3,339 | 3,339 | PASS |
| Stored comparison or baseline left on a non-version | 0 (1,792 cleared) | 0 and 0 | PASS |
| Baselines that point at a non-version | 0 | 0 | PASS |
| Baselines left | all on the Introduced paper | 971 documents with a baseline; all 971 point at an "Introduced" paper | PASS |

I cannot read the "820 re-based" line as a number on the replica (I have no copy of the earlier baselines), but the end state is what it should be: every remaining baseline is the Introduced paper and none sits on an amendment.

## Next on my side
Build the manifest pull request that re-applies #501 (the revert of #507), then its rollout request. Open item still for Ramon: a not-enacted bill's only real version is now its Introduced text.

Tickets: OPEN-672, OPEN-907, OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
