# Request: load the legislators for Pennsylvania, Nebraska and Louisiana into production, then re-import the data already collected (NO rescrape), OPEN-478, 479, 480, 2026-11-03

**Ramon's go (this session, /ask-me, 2026-11-03): "Yes, ask the prod agent now".** This is a production write. It has stop conditions; please read them first. **The LegBot request (`36df545`) is separate and still wanted.**

## What went wrong (my omission, not yours)
The first scrapes of `pa`, `ne` and `la` loaded cleanly, but **production has 0 legislators for all three states**, so every vote and sponsorship was stored with a name and no person. My Stage 2 request did not include runbook rule 1 (people before the first import). Read-only Stage 3 gates (`quality_check.py --structural`, against the logical replica, 2026-11-03):

| State | People in production | Votes with no person | Sponsorships with no person |
|---|---|---|---|
| PA | 0 | 425,560 of 425,560 | 71,231 of 71,231 |
| NE | 0 | 86,723 of 86,723 | 2,296 of 2,296 |
| LA | 0 | 230,721 of 230,721 | 10,783 of 10,783 |

(For comparison, the same database holds 587 people for NC and 571 for MI.) The counts of bills, vote events and person votes are right; they are only not linked to legislators. **No LegBot, routing, archive or embedding has run on these states**, so nothing public depends on them yet.

## Before you change anything (read-only; tell me before step 1 if any answer is "no")
1. Nothing is running for these states or in the in-flight store; no ddp-sync job is near; **it is not close to Sunday 02:00 UTC** (the batch now includes these three states).
2. **Read the people data you would load:** the production people checkout's revision (give `git rev-parse HEAD`) and confirm `data/pa`, `data/ne` and `data/la` exist with legislator files. Expected legislators: PA about 253 (203 House, 50 Senate), NE 49 (unicameral), LA about 144 (105 House, 39 or 40 Senate). Report the counts of files you see.
3. **Tell me how you will run the re-import** and what it reads (the already-collected output of the 11-02 runs, in S3 or the collector, or a re-scrape). **If the only way is a new scrape, STOP and ask Ramon**: he asked for no rescrape. Use the same sanctioned path you used for NC's fix (people load, then a plain `os-update <st> --import`); do not hand-roll anything.

## Then, one state at a time (Nebraska first: smallest, then Louisiana, then Pennsylvania)
* **Record before:** bills, vote events, person votes, sponsorships, people for the state (read-only).
* `os-people to-database <st>` for the state; read the people count back (expect the numbers above).
* The re-import for that state, from the collected data. The summary may show vote or bill changes: **record it in full**.
* **Record after, and compare:** bills, vote events and person votes must **equal the "before" numbers** (NE 1,847 / 1,772 / 86,723; LA 2,616 / 3,172 / 230,721; PA 5,270 / 5,858 / 425,560). People must be above 0. Votes and sponsorships with no person must fall to a small share (the gate ceiling is 4.7%); give the exact numbers and the names of the top 5 unmatched voters, if any.
* Run the read-only gates again: `quality_check.py --structural <st>` (from the dev checkout's venv, or tell me how you ran it). Report the five gate lines.

## Stop and tell me (change nothing further, delete nothing)
* The re-import changes the **bill, vote-event or person-vote count** for the state, or deletes anything.
* Any error, a non-zero exit, a load that fails or runs past its time limit.
* The people files for a state are missing or the counts are far from expected.
* Unresolved votes or sponsorships stay above 4.7% after the fix (report the top unmatched names; do not edit anything).
* Anything touches a state other than `pa`, `ne` or `la`.

## Do not
No new scrape, no restart of ddp-sync, no config or `.env` edit, no LegBot, archive, routing or embedding, no deletion. The manifest flag `people_refresh` for the three states is a separate change that I will make through a PR; it is not part of this request.

**Reply with a note on this branch:** the steps above with times, the before and after numbers per state, the five gate lines per state, and anything you stopped on.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
