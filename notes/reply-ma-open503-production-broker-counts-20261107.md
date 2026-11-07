# Reply (read-only): the 2,445 flagged Massachusetts bills in the PRODUCTION broker (OPEN-503). 2026-11-07, 19:35-19:38 UTC

Reply to 64a335f4. **Counts only. Nothing was written, changed or deleted** (queries in the web container's Django shell, no `save`/`delete`/`update`). No removal was run.

**The user's go (this session, verbatim):** "Yes, run the read-only counts now (Recommended)".

## Two things that would have misled you (read these first)
1. **Identifiers.** Production writes Massachusetts identifiers **without a space** (`HD4365`, `S2719`, `H5664`); your CSV has `HD 4365`. I removed the space before matching (my first try matched 0 of 2,445 for that reason).
2. **How versions link to bills.** `BillVersion.bill` points to the bill's **OpenStates id** (`Bill.primary_openstates_id`), not its numeric id. A query that joins on the numeric `Bill.id` finds **no versions and no artifacts**. My first count did exactly that and showed zero; the public endpoint showed artifacts for the same bills, which is how I caught it. All numbers below use the Django relation (`bill__in=<the Bill rows>`), which follows the right key. If any of your own queries join on the numeric id, they will read zero too.

## Method
Bills: `Bill` rows with `session__jurisdiction__iso2='MA'`, session `194th`, `gov_id` in your list with spaces removed. Artifacts: `BillArtifact` through `bill_version__bill`. Script and output kept on this host (`open503_counts_v2.py` / `.out` in the job scratch).

## Your five questions
1. **In the production broker: all 2,445 of 2,445** (none missing; none has more than one Bill row; all in session `194th`). By group: Other (subject-only titles, orders, filings) 608; Communication 606; Report 556; Order relative to ... 304; Study order 167; Amendment paper 156; Annual report 35; Precept 4; Message 3; Rules 3; Proposed rules / filings 3. (Production has 11,044 Massachusetts Bill rows in total.)
2. **Artifacts: 19,560 on all 2,445 bills.** Eight types, exactly one of each per bill: bill_summary, bill_pros_cons, bill_vote_yes_frame, bill_vote_no_frame, bill_supporting_orgs, bill_opposing_orgs, bill_impact_analysis, bill_topics (no changelogs). Versions: 2,445 (one per bill). Status: **complete + approved 6,814** and **failed + approved 12,746**; nothing pending, nothing pending review.
   **"Published", as I decided it:** the broker's public read endpoints serve an artifact only when it is `complete` and `approved` (the rule stated in `common/admin.py`). By that rule **6,814 artifacts on 1,808 bills are published**; the other 637 bills have only failed artifacts. I found **no bill-level Webflow item or page field** in the broker (the only external id on a bill is the legacy OpenStates id), so I cannot say which have a Webflow page; that side is not visible here.
3. **Timing:** all 19,560 were generated **before** 2026-11-06 22:00 UTC; **none after**. Earliest 2026-10-09 05:05 UTC, latest **2026-11-06 06:04 UTC** (about 16 hours before the rule). So the data cannot show whether the rule stopped new ones: none were being generated in that window.
4. **Real edits or people's input: none found.** Staff-edited artifacts (`edited_by` set): 0. Artifacts with a person's review (`reviewed_by` set): 0. Artifacts whose origin is not `ai_generated`: 0; revising another artifact: 0. Poll tallies (`Tally`): 0 bills. Votes (`Motion`): 0. Organization positions found by the model: 0 (they are model-found, not a person's, in any case). `LegBotRequest` rows: 0. Voatz poll promotions for these gov_ids: 0. Follows: production has **0 alert rules at all** (my baseline count), so none on these bills; the alert model has no direct bill link I could query. **Not checked:** a staff edit of the bill's own title or description (I have no history for those fields), and anything that lives only on Webflow or the website.
5. **Does a hidden document still show on a bill page? Partly answered, from the broker side only.** For five random bills (S2719, H5665, HD4395, SD3207, SD3069) I read the **public API the website reads**, not the website:
   - `/api/bill-artifacts/current/` returns `found: true` with artifacts for three of them (S2719 4,747 bytes of summary and analysis, H5665 4,240, HD4395 1,003) and an empty set for SD3207 and SD3069 (their artifacts are the failed ones).
   - `/api/bill-versions/history/` and `/latest/` return the one version for all five (`version_note: "Bill Text"`, **`text_url` empty, `version_date` empty, `chunk_count` 0**): the version exists but has no document link or text in the broker. (`/api/bills/<id>/scorecard/` is 404 for all five; they have no scorecard.)
   - So: **the published artifacts of these bills are still served by the broker's public endpoints** (that is what the OPEN-498 rule does not change), and the version rows are still there with no text. I **cannot see the website's Documents card, full-text tab or version-history page**, so I do not know what a visitor sees there; that needs a look at the site.

## Not done
No removal, no edit, no write of any kind; no search refresh; no cleanup. Waiting for Ramon's GO in a separate note for any removal plan.
