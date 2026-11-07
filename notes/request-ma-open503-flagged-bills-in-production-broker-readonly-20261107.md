# Request (READ-ONLY): how many of the Massachusetts reports and orders that OPEN-498 now hides are in the PRODUCTION broker, and do they have artifacts or published pages? (OPEN-503). 2026-11-07 (Mac side)

**Nothing is to be written, changed or deleted.** This is counting. A removal plan comes later, only after Ramon has seen your numbers and says GO in a separate note.

**Why.** OPEN-498 marked 3,200 Massachusetts documents "not a real bill" on RDS (your `b234740`). That stops new reports and orders from being analysed, but bills that ddp-sync had already put in the broker before the rule are untouched. On the Mac's dev side the ddp-sync log shows 2,445 of the 3,267 title-flagged bills ensured in the broker. Ramon (2026-11-07): sample them, and if none is a real bill, remove them from the broker. A read of 47 random ones found 0 real bills (OPEN-503).

**The list.** `notes/ma-open503-flagged-bills-in-dev-broker-20261107.csv` on this branch: 2,445 rows (`bill`, `title`, `group`), Massachusetts 194th session, bill numbers such as `HD 4365`. Public data only.

**Please report (counts, plus the query you used):**
1. How many of the 2,445 exist as Bill rows in the production broker (the production broker, not the Mac's dev one), by `group`.
2. Of those, how many have any bill artifact (summary, changelog, concept statements, positions, anything generated), and how many have a *published* page or Webflow item. Say how you decided "published".
3. Of the artifacts, how many were written after 2026-11-06 22:00 UTC versus before (so we see whether the new rule already stopped them).
4. Any bill in the list whose broker row has a real (non-AI) edit by staff, or a poll or position by a person. Those must not be removed with the rest.
5. Does a hidden document still show anywhere on a bill page for one of them (the Documents card, the full-text tab, version history)? Pick 5 and say which page you looked at, if you can; if you cannot, say so.

**Reply** `reply-ma-open503-production-broker-counts-20261107.md`. Do not run any removal. The same run-quiet gates apply to any query heavy enough to matter; these should not be.
