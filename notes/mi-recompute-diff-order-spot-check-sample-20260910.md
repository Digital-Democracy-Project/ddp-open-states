# MI recompute-diff-order dry-run: real corrected-document sample for a Mac-side spot-check

*For `notes/rds-backfill-commit-approved-order-20260910.md`'s Step 4 (spot-check before
committing).* `recompute-diff-order mi --dry-run` came back: `3930 bills checked | unchanged=11794
corrected=1803 nulled=0` -- higher than the ~1,519 historical estimate but a real number, not
alarming on its own (real RDS data legitimately differs from the historical estimate, per the
plan's own note).

Pulled 8 real "corrected" documents directly (calling `recompute_bill_diff_order()` -- the pure,
read-only half of the command -- against real bills, nothing committed) with full identifiers and
both the currently-stored diff and the newly-computed one, so you can pull the same
`BillVersionDocument` rows on the Mac's local Postgres and confirm they match what this fix
should produce.


================================================================================
bill.identifier: SB 695
bill.id: ocd-bill/3444c454-ab09-488e-b741-6c45b822f405
legislative_session: 2025-2026
BillVersionDocument.id: 96810
version_note: 'As Passed by the Senate'
version_date: ''
media_type: text/html
source_url: https://legislature.mi.gov/documents/2025-2026/billengrossed/Senate/htm/2025-SEBS-0695.htm
CURRENT diff_from_previous_version (len): 6598
NEWLY COMPUTED diff (len): 545
CURRENT diff first 200 chars: '--- \n+++ \n@@ -1,55 +1,84 @@\n-Sec. 801j. (1) Except as otherwise provided in subsection (6),\n-in addition to the required vehicle registration tax under section\n-801(1)(p), a regional transit authority'
NEW diff first 200 chars: '--- \n+++ \n@@ -59,9 +59,8 @@\n defects, or suggesting product or production improvements as an ordinary and\n necessary business expense of the manufacturer.\n \n-Enacting section 1. This amendatory act ta'
================================================================================
bill.identifier: SB 87
bill.id: ocd-bill/1528409b-9dae-4a1d-ab5e-5c9661f6c43a
legislative_session: 2025-2026
BillVersionDocument.id: 98523
version_note: 'As Passed by the Senate'
version_date: ''
media_type: text/html
source_url: https://legislature.mi.gov/documents/2025-2026/billengrossed/Senate/htm/2025-SEBS-0087.htm
CURRENT diff_from_previous_version (len): 828
NEWLY COMPUTED diff (len): 0
CURRENT diff first 200 chars: '--- \n+++ \n@@ -1,5 +1,40 @@\n-Sec. 804. The commission shall suspend the license of a\n-retailer for 14 days if the retailer has made 6 or more payments to\n-a wholesaler that have been dishonored by a fi'
NEW diff first 200 chars: ''
================================================================================
bill.identifier: HB 4340
bill.id: ocd-bill/11ea4b06-3129-45e9-a668-515155c77aa7
legislative_session: 2025-2026
BillVersionDocument.id: 98861
version_note: 'As Passed by the House'
version_date: ''
media_type: text/html
source_url: https://legislature.mi.gov/documents/2025-2026/billengrossed/House/htm/2025-HEBH-4340.htm
CURRENT diff_from_previous_version (len): 844
NEWLY COMPUTED diff (len): 0
CURRENT diff first 200 chars: '--- \n+++ \n@@ -1,6 +1,46 @@\n-Sec. 1d. (1) Except as otherwise provided under federal law,\n-an individual shall not receive services or grants or participate\n-in any program under this act unless the in'
NEW diff first 200 chars: ''
================================================================================
bill.identifier: HB 4242
bill.id: ocd-bill/882392f7-8fe2-4d6a-92ef-71165933e5b4
legislative_session: 2025-2026
BillVersionDocument.id: 100343
version_note: 'As Passed by the House'
version_date: ''
media_type: text/html
source_url: https://legislature.mi.gov/documents/2025-2026/billengrossed/House/htm/2025-HEBH-4242.htm
CURRENT diff_from_previous_version (len): 28221
NEWLY COMPUTED diff (len): 0
CURRENT diff first 200 chars: '--- \n+++ \n@@ -1,235 +1,305 @@\n-Sec. 16213. (1) A licensee shall keep and maintain a record\n-for each patient for whom the licensee has provided medical\n-services, including a full and complete record '
NEW diff first 200 chars: ''
================================================================================
bill.identifier: HB 4697
bill.id: ocd-bill/8434a6b3-7f4f-48ab-919d-41869c28f7d3
legislative_session: 2025-2026
BillVersionDocument.id: 93391
version_note: 'As Passed by the House'
version_date: ''
media_type: text/html
source_url: https://legislature.mi.gov/documents/2025-2026/billengrossed/House/htm/2025-HEBH-4697.htm
CURRENT diff_from_previous_version (len): 7321
NEWLY COMPUTED diff (len): 0
CURRENT diff first 200 chars: '--- \n+++ \n@@ -1,62 +1,104 @@\n-Sec. 4. (1) Subject to subsection (2), (3), a prospective\n-guardian who meets all of the following criteria may receive be\n-approved by the department for guardianship as'
NEW diff first 200 chars: ''
================================================================================
bill.identifier: HB 4080
bill.id: ocd-bill/d111f239-6404-457b-910b-e5fda3e2fdca
legislative_session: 2025-2026
BillVersionDocument.id: 96359
version_note: 'As Passed by the House'
version_date: ''
media_type: text/html
source_url: https://legislature.mi.gov/documents/2025-2026/billengrossed/House/htm/2025-HEBH-4080.htm
CURRENT diff_from_previous_version (len): 10598
NEWLY COMPUTED diff (len): 5350
CURRENT diff first 200 chars: '--- \n+++ \n@@ -1,85 +1,135 @@\n-Sec. 1. As used in this act:\n-(a) "Department" means the department of treasury.\n-(b) "Totally and permanently disabled" means a person as\n-defined in 42 U.S.C. section 4'
NEW diff first 200 chars: '--- \n+++ \n@@ -5,30 +5,28 @@\n (a)\n "Department" means the department of treasury.\n \n-(b) "Totally\n-and permanently disabled" means a person as\n-defined an individual described in 42 U.S.C. section 416.'
================================================================================
bill.identifier: SB 866
bill.id: ocd-bill/ef643330-445c-4189-a464-0bd012978a3f
legislative_session: 2025-2026
BillVersionDocument.id: 90092
version_note: 'Substitute (S-1)'
version_date: ''
media_type: application/pdf
source_url: https://legislature.mi.gov/Home/GetObject?objectName=2026-SCVBS-0866-00B76.pdf
CURRENT diff_from_previous_version (len): 91568
NEWLY COMPUTED diff (len): 86905
CURRENT diff first 200 chars: '--- \n+++ \n@@ -4,16 +4,1613 @@\n corrections for the fiscal year ending September 30, 2027, from the\n following funds:\n DEPARTMENT OF CORRECTIONS\n-GROSS APPROPRIATION                                    '
NEW diff first 200 chars: '--- \n+++ \n@@ -4,16 +4,1613 @@\n corrections for the fiscal year ending September 30, 2027, from the\n following funds:\n DEPARTMENT OF CORRECTIONS\n-GROSS APPROPRIATION $ 100\n-State general fund/general p'
================================================================================
bill.identifier: HB 4354
bill.id: ocd-bill/38c537b3-0508-46b6-aec8-67154ea164ae
legislative_session: 2025-2026
BillVersionDocument.id: 92447
version_note: 'As Passed by the House'
version_date: ''
media_type: text/html
source_url: https://legislature.mi.gov/documents/2025-2026/billengrossed/House/htm/2025-HEBH-4354.htm
CURRENT diff_from_previous_version (len): 32287
NEWLY COMPUTED diff (len): 592
CURRENT diff first 200 chars: '--- \n+++ \n@@ -1,295 +1,448 @@\n+\n+\n+ \n+\n+ \n+\n+ \n+\n+ \n+\n+ \n+\n+ \n+\n+ \n+\n+ \n+\n+ \n+\n+HOUSE BILL NO. 4354\n+\n+\n+\n+A bill to amend 1965 PA 203, entitled\n+\n+"Michigan commission on law enforcement standards\n+a'
NEW diff first 200 chars: '--- \n+++ \n@@ -221,9 +221,9 @@\n 35, MCL 124.1 to 124.13.\n \n (II) A law\n-enforcement officer licensed under this act whose duties are performed in conjunction\n-with an interlocal agreement entered into '

## Ask

Pick a couple of these (or all 8, your call) and confirm the "newly computed" diff matches what
`recompute_bill_diff_order()` produces against the same rows on the Mac's local Postgres -- that's
the real acceptance check per the plan, not just "the counts look plausible." I don't have Mac
Postgres access from this EC2 host, so this is the concrete data point needed before I run
`--commit` for `mi`.

Once confirmed, I'll proceed with `recompute-diff-order mi --commit`, spot-check one `nulled` and
one `corrected` result from the actual commit output, and report back before starting `ut`.
