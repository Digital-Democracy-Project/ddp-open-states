# OPEN-424: targeted Michigan rescrape plan (not run)

Written 2026-10-26. **Nothing here has been run.** It needs (1) the parser fix (openstates-scrapers PR for OPEN-424, on top of the catch-up, OPEN-401) merged to fork `main` and live where the run happens, and (2) named approval from the data owner recorded on OPEN-424 (RUNBOOK, "Verifying a Michigan scraper fix against the live site", steps 2-3 write to the production database).

## What it repairs
Stored 2025-2026 Michigan roll calls whose voters disagree with the tally printed in their own motion text (`check-mi-vote-tallies.py`, read-only): **128 votes** (84 Senate, 44 House). Replaying every real journal page in the Mac's scrapelib cache (198 pages, 1,324 roll calls) through the fixed parser, joined to every stored vote:

| | votes |
|---|---|
| disagree today | 128 (Senate: 62 no Yea voters, 22 other shape; House: 44) |
| the fixed parser matches the official tally | 118 (Senate 80, House 38) |
| no cached journal, cannot check | 4 (HB 5249, SB 373, HB 4746, HB 5570; all 2026-07-03 Senate) |
| still wrong with the fix | 6 (House, 2026-07-03: HB 6074, HB 4103, HB 4396, HB 4309, HB 4518, SB 423) |
| right today, would become wrong | 0 for the bills listed below; **HB 4543** (Senate 2025-12-16, roll call 343) would, so it is excluded |

## Accounting (how the numbers fit)
* The replay changed the parse of **27** roll calls (22 became exact, 5 stayed wrong: House 331, 332, 333, 339 and Senate 343 = HB 4543).
* **128** stored votes disagree today. **118** of them become exact. **4** cannot be checked (journal not cached). **6** stay wrong: the House votes of HB 4309, HB 4396, HB 4103, HB 6074, HB 4518 (journal layout) and SB 423.
* The rescrape list is by bill, because a rescrape replaces all of a bill's votes: **95 bills, 241 stored votes** (`open424-mi-rescrape-votes.csv` has one row per vote: stored today, journal cached, expected after). 111 are right today and stay right; 118 become right; 5 stay wrong (the four House votes above on bills that are listed for their other votes, plus HB 4518's); 4 are wrong today and unverifiable; **3 are right today and unverifiable** (SB 433 House 2026-09-22 and Senate 2026-10-01, SB 478 House 2026-09-22; their journals are newer than the cache). HB 4543 and SB 423 are not in the list.
* Why the 5 stay in: for the four 105-yes/1-no House votes the change is 106/0, and the one nay it drops (Rep. Young) was an alphabetical Yea, so it is a strict improvement for him; the two real nays are recorded as yeas before and after. HB 4518 is 108/0 before and after.
* Why the 4 + 3 unverifiable stay in: the first four are wrong today, so a rescrape cannot make them worse in the way that matters, and the 3 are flagged for the first thing to look at after the run.

## The run
`open424-mi-rescrape-bills.txt`: the 95 bills above (HB 5570 is in both the repairable and the unverified groups). **HB 4543 is excluded by name** (its Senate roll call 343 is right today and would become wrong); SB 423 is not listed.

**Order and revisions:** (1) the catch-up (OPEN-401, openstates-scrapers PR #73) is merged to fork `main`; (2) openstates-scrapers PR #77 (OPEN-424) is merged on top; (3) the run happens where that merged `main` is live: the Mac after its 01:00 UTC pull, or Fargate after the image deploy that carries both (the deploy is on hold, OPEN-437). Write the fork `main` commit hash on the ticket before running.

Four runs of at most 25 bills, not one run of 95: `run-scrape.sh` names its marker files after the whole argument string, and a 95-bill list is a 700-byte name (the limit is 255; the same fault is OPEN-432's, tried there: `File name too long`). `notes/open424-mi-rescrape-runs.txt` holds the four lines (25 bills is at most 212 bytes with its suffix). The cost: `bill_no=` still walks the search listing and only skips the per-bill fetch for other bills, so the listing is paid four times; **measure the first run's requests and stop if the listing alone is large**, and use fewer, longer runs only if the data owner accepts that.

**Stop at the first failed run, a WAF block warning, or clearly more requests than below; do not retry by hand.**

```
source activate.sh
while read -r list; do ./run-scrape.sh mi "session=2025-2026 bill_no=$list" || break; done < notes/open424-mi-rescrape-runs.txt
```

`run-scrape.sh` has no marker for such an argument, so each run is full-mode with no `start=` cutoff (the same reason as OPEN-432). (`bill_no=` accepts `SB415`, `SB 415` and `sb 0415`; RUNBOOK explains the two formats.)

**Expected live cost to write on the ticket:** the search listing windows, plus 95 bill pages. The 241 votes cite 72 distinct journal pages; the Mac's `_cache` serves 234 of the 241 votes (on Fargate, which has no cache, all 72 pages are fetched).

## Before and after (the same tally comparison)
```
OPENSTATES_DB_NAME=<db api-v3 serves> ./check-mi-vote-tallies.py --list                      # before: 128 disagree
OPENSTATES_DB_NAME=<db api-v3 serves> ./check-mi-vote-tallies.py --bills notes/open424-mi-rescrape-bills.txt --list
# ...run...
OPENSTATES_DB_NAME=<db api-v3 serves> ./check-mi-vote-tallies.py --bills notes/open424-mi-rescrape-bills.txt --list   # after
```
**Pass:** disagreeing votes across all of 2025-2026 fall from 128 to **at most 10**, and the ones left are exactly: the 6 House votes above, plus 0 to 4 of the unverified Senate votes of 2026-07-03 (look at each by hand against the journal). Any other disagreement, any vote that was right before and disagrees now (compare with the CSV; the 3 unverifiable ones first), or a count above 10, means stop and report; fixing it is a corrected rescrape of the same `bill_no=`, not a delete (RUNBOOK).

Two more checks, because a rescrape rewrites a bill's whole vote:
* Per-voter rows of the 6 still-wrong House votes (the journal prints the two nays inside the Yeas rows): stored 105 yes / 1 no becomes 106 / 0. The one stored nay (Rep. Young) was wrong (an alphabetical Yea), so the change is a strict improvement for him; the two real nays stay recorded as yeas either way. Tracked as a follow-up ticket.
* Voters that resolve to nobody (`voter_id IS NULL`) in the rescraped votes, before and after, so O'Neal-style name gaps (OPEN-425) are not mistaken for this fix.

## Not covered
* HB 4543's Senate roll call (the journal prints 33 names under "Yeas—31" and 2 under "Nays—4", contradicting its own counts): no parser can be exact; it stays as stored.
* Votes whose journal page is not in the cache (58 of 1,279 stored): unverified; the check script flags them if their stored voters disagree with their tally.
