# REPLY to `9ce177b` (nothing for you to do now): **ND text refresh and RI relabel verified on the Mac replica. ND recompute: my range is 3 flag changes and nothing else; the empty list is explained. The commit waits on Ramon's second go.** 2026-11-24 ~21:10 UTC (Mac side, Onboard New States)

**Not a GO.** No ND recompute commit is authorized by this note.

## Verified on the replica (read at 21:01–21:02 UTC)
* **RI relabel:** actions still carrying `committee-failure` in Rhode Island: **0** (was 2,222). Verified.
* **ND text refresh:** Dakota documents **2,690** (your backup count); **1,464** rewritten after 20:50 UTC (your commit: 1,431 stale documents, 850 comparisons corrected, so 1,464 is the right order). Verified.

## ND recompute: the oddity you flagged is explained
I re-ran `recompute-diff-order nd --dry-run` on the replica at core `70146fac` (read-only; it reproduces your numbers exactly: `unchanged=2690 corrected=0 nulled=0`, `is_bill_version set=0 changed=3 not_a_version=3`, baselines 0, **list 0 documents**).
* **Why `changed=3` with an empty list:** the change list records comparison and baseline changes only. The `is_bill_version` flag flips are counted in the summary but are **not in the list** (core `text_extract.py`, the flag loop after the baseline step). So an empty list does **not** mean nothing changes.
* **The three documents (read by running core's own `_is_bill_version` on each stored document):**
    * **SB 2308**, "SECOND ENGROSSMENT - NOT ADOPTED"
    * **SCR 4022**, "FIRST ENGROSSMENT - NOT ADOPTED"
    * **SB 2400**, "SECOND ENGROSSMENT - NOT ADOPTED"
    * Each is stored `is_bill_version = true` and the rules say **false**: an engrossment that was not adopted is not the bill's text.
* **Range I expect at the commit:** `is_bill_version changed=3 not_a_version=3`, `corrected=0 nulled=0`, baselines 0, list 0 documents. Nothing else changes.
* **Because the list is empty, the commit's `--list` and `--expect` guard cannot protect the flag change.** So Ramon should see these three before he says go. I recommend committing: all three are plainly "not adopted", and nothing downstream changes (no comparison or baseline moves). **Your call on the order with ND's launch; I am not asking for it now.**

## Still open
Maine archive (no end line yet at 21:00); OK 2026, KY, HI, MO and IA loads; the v90 request `85ce7f0`.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
