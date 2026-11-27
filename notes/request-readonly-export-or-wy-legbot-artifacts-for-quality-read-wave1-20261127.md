# REQUEST (read-only; not a production change): **an export of about 15 Oregon and 15 Wyoming LegBot artifacts so I can read them for quality.** 2026-11-27 ~01:45 UTC (Mac side, Onboard New States)

**Why:** Ramon's wave rule is that the gate is data quality: someone reads the LegBot summaries and judges whether they are good or garbage. Your 11-26 results (Oregon 919 artifacts, 844 complete; Wyoming 834, 758 complete; `97bb399`/`c64bb44`) say nobody has read the production ones. I read about 20 dev ones on 11-25/26; these are the real production run, and I cannot read the broker's production artifact table from the Mac.

## What I need from you
1. **Choose the bills:** from the two sample lists you saved (the 100-bill sample per state), take **15 Oregon and 15 Wyoming bills** spread across: enacted, failed or died in committee, one-version and multi-version bills, a long bill (over 50,000 characters), and at least 2 bills that had a failed artifact. Use a stable rule (for example every 7th bill of each sorted list, then swap in the long and failed ones) and **say which rule** so the sample is not cherry-picked.
2. **Export, read-only, as plain text:** for each chosen bill, one block: state, session, bill identifier, then for each artifact of types `bill_summary`, `bill_changelog`, `bill_pros_cons` and `bill_impact_analysis`: its status, its version note, its `model_name`/`origin`, and its content (the text only). No hostnames, no ids that open a door, no keys.
3. **Do not put the export in a note on this branch** (it is unreleased AI output on a public branch). **Give the file to Ramon in your session**; he hands it to me (a file path on the Mac I can read). Tell me here in one line when it is given ("export given to Ramon in session") and the sampling rule you used.

## Not authorized
Any write; any regeneration or retry of a failed artifact; any other state or session; exporting more than the 30 bills.

## What I do with it
I read each artifact against the bill's stored text and actions on the Mac replica (good / problem + a one-line reason), count problems by kind, and post the result as a Jira comment and a `reply-` note (counts and bill ids only, no artifact text), with my verdict on whether Oregon and Wyoming are safe for the public switches. Tickets: OPEN-897 (wave 1), OPEN-589, OPEN-662; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
