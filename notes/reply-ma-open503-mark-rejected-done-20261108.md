# Reply: the artifacts of the 2,445 flagged Massachusetts bills are marked REJECTED in the production broker, and everything checks out (OPEN-503). 2026-11-08, 19:32 UTC

Reply to your GO `9e55a9b` (Part 2 of `39694f4`). **Done in one run, verified, nothing deleted.** No Webflow, website, search index or other state was touched.

## The user's words (this session, verbatim)
- Go: **"Yes, hide them now (Recommended)"** (their question: hide the computer-written summaries for the 2,445 non-bill items, nothing deleted, can be un-hidden).
- Whose name to record: **"Ramon Perez"**, so **`reviewed_by` = `ramon.perez`** on every row.
(I took your relayed GO as information and asked first; the preflight was `dfaa34c`.)

## Gates and the run
- **Preconditions re-read at 19:29 UTC** (as your GO required): 2,445 of 2,445 bills; **19,560 artifacts**: **6,814 complete + approved, 12,746 failed + approved**, nothing else; **0 staff-edited, 0 with a person's review (`reviewed_by`), 0 non-AI origin**. Baselines: public topic rows on these bills 3,361; all Massachusetts public topic rows 23,146; approved artifacts of all other bills 339,986; rejected 1,016; Massachusetts bills 11,044. All as in the preflight.
- **Restore point:** the broker database `data-broker-postgres-3` showed latest restorable time **2026-11-08T19:24:31Z** just before the change (7-day retention).
- **Undo list saved:** `(id, status, review_status, reviewed_by id, reviewed_at)` for all **19,560** artifacts, on this host (`~/ops/ma-open503-artifacts-before-reject-20261108.txt`, mode 600, 19,560 lines; not committed to the repo). Rollback as you described: set those rows back to `approved` with `reviewed_by` empty (every one had `reviewed_by` empty and `reviewed_at` set before).
- **The change (19:29:59 to 19:30:39 UTC):** per row, `review_status = REJECTED`, `reviewed_by = ramon.perez`, `save()` (not `queryset.update()`), inside **one transaction that checked its own counts before committing and would have rolled back on any difference**: it committed. **19,560 rows in 36.6 s.** (The window was not quiet in the Sunday-batch sense; it ran 19:30 UTC with the 30-minute map chain running; none of that touches artifacts.)

## Your verification
- **No `complete` + `approved` artifact remains for these bills (0), and no approved artifact of any kind (0).** After: **complete + rejected 6,814, failed + rejected 12,746**, all 19,560 with `reviewed_by` `ramon.perez` (the only reviewer).
- **Public topics:** `public_bill_topics()` rows on the flagged bills **3,361 to 0**; the `BillTopic` rows are still there (3,361), only hidden by the rejected-source rule; **all Massachusetts public topic rows 23,146 to 19,785**, as on dev.
- **The five bills** (S2719, H5665, HD4395, SD3207, SD3069): `/api/bill-artifacts/current/` answers **200 with `found: true` and 0 artifacts each** (an empty set, as your dev test showed, not `found: false`).
- **Nothing else changed:** Massachusetts bills in the broker still **11,044**; approved artifacts of all other bills still **339,986** (and all approved now 339,986, since none of these remain approved); **rejected total 1,016 to 20,576** (+19,560 exactly).
- **No errors:** no Traceback or ERROR in the web or celery logs since the change (the only earlier ones in this window were an outside scanner's bare-IP requests, unrelated); `/api/status/` 200. As in the preflight, a rejection triggers no sync or task (the topic-sync receiver ignores rejections), and nothing from these bills was ever in the vector store.

## Reminders
- The rows stay and can be re-approved from the admin. With `reviewed_by` set, a later regeneration of any of these artifacts would land `pending_review` (hidden), not approved (BROKER-272).
- **Not covered, because I cannot see it from here:** the website's own pages and caches, Webflow, anything on the Mac. If a rejected page still shows on the site after its cache expires, that is outside what I changed.
- **Not done (as you said):** Webflow, the website, search indexes, the other states, deletion; and OPEN-396 is untouched.
