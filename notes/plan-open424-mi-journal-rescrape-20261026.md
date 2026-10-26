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

## The run
`open424-mi-rescrape-bills.txt`: **95 bills** (92 with a vote the fix repairs, plus the 4 unverified ones; HB 5570 is in both). HB 4543 is not in it. SB 423 is not in it (its only flagged vote stays wrong either way).

One run, not 95: `bill_no=` still walks the search listing and only skips the per-bill fetch for other bills, so one comma list pays the listing cost once.

```
source activate.sh
./run-scrape.sh mi session=2025-2026 bill_no=HB4023,HB4042,HB4062,HB4063,HB4064,HB4072,HB4100,HB4101,HB4103,HB4104,HB4180,HB4181,HB4182,HB4183,HB4187,HB4189,HB4207,HB4208,HB4309,HB4350,HB4392,HB4396,HB4415,HB4471,HB4517,HB4518,HB4644,HB4706,HB4724,HB4746,HB4750,HB4779,HB4805,HB4808,HB4824,HB4951,HB4961,HB4968,HB5232,HB5233,HB5249,HB5570,HB5571,HB5630,HB5646,HB5697,HB5806,HB5807,HB5995,HB6043,HB6074,SB105,SB1052,SB106,SB133,SB160,SB166,SB18,SB205,SB22,SB273,SB293,SB294,SB349,SB373,SB415,SB418,SB421,SB433,SB456,SB478,SB501,SB52,SB527,SB569,SB577,SB578,SB579,SB585,SB586,SB604,SB616,SB71,SB716,SB721,SB722,SB723,SB792,SB793,SB81,SB878,SB903,SB913,SB966,SB989
```

(`bill_no=` accepts `SB415`, `SB 415` and `sb 0415`; RUNBOOK explains the two formats.) Run it where the fixed parser is: the Mac after its 01:00 UTC pull of fork `main`, or Fargate after the image deploy that carries the fix (the image deploy is on hold, OPEN-437).

**Expected live cost to write on the ticket:** the search listing windows, plus 95 bill pages. The 241 votes of these bills cite 72 distinct journal pages, and 234 of the 241 are already in the Mac's `_cache` (served without a request there; on Fargate, which has no cache, all 72 are fetched). Stop the run if it makes clearly more requests than that, or logs a WAF block: Michigan is the one jurisdiction where over-scraping costs more than the problem.

## Before and after (the same tally comparison)
```
OPENSTATES_DB_NAME=<db api-v3 serves> ./check-mi-vote-tallies.py --list                      # before: 128 disagree
OPENSTATES_DB_NAME=<db api-v3 serves> ./check-mi-vote-tallies.py --bills notes/open424-mi-rescrape-bills.txt --list
# ...run...
OPENSTATES_DB_NAME=<db api-v3 serves> ./check-mi-vote-tallies.py --bills notes/open424-mi-rescrape-bills.txt --list   # after
```
Pass: the 118 repairable votes agree; the remaining disagreements are exactly the 6 House votes above, the 4 unverified ones (look at each by hand against the journal) and HB 4543; no vote that agreed before disagrees now.

Two more checks, because a rescrape rewrites a bill's whole vote:
* Per-voter rows of the 6 still-wrong House votes (the journal prints the two nays inside the Yeas rows): stored 105 yes / 1 no becomes 106 / 0. The one stored nay (Rep. Young) was wrong (an alphabetical Yea), so the change is a strict improvement for him; the two real nays stay recorded as yeas either way. Tracked as a follow-up ticket.
* Voters that resolve to nobody (`voter_id IS NULL`) in the rescraped votes, before and after, so O'Neal-style name gaps (OPEN-425) are not mistaken for this fix.

## Not covered
* HB 4543's Senate roll call (the journal prints 33 names under "Yeas—31" and 2 under "Nays—4", contradicting its own counts): no parser can be exact; it stays as stored.
* Votes whose journal page is not in the cache (58 of 1,279 stored): unverified; the check script flags them if their stored voters disagree with their tally.
