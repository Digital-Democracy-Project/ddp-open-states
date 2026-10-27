# OPEN-432: targeted Washington rescrape to fill the missing chapter citations (not run)

Written 2026-10-26. **Nothing here has been run.** A rescrape writes to the production database through the normal import, so run it only with the data owner's go-ahead recorded on OPEN-432.

## What is missing (read-only, `check-wa-chapter-citations.py`, the database api-v3 serves)
| session | bills | with a "Chapter N, YYYY Laws" action | citation stored | **missing** |
|---|---|---|---|---|
| 2025-2026 | 3,411 | 690 | 196 | **494** |

**No earlier session is stored here:** this database holds Washington bills for 2025-2026 only (the sessions 2009-2010 to 2023-2024 exist as session rows with no bills), so 2023-2024 cannot show the gap here. The script reports every Washington session it finds; run it once on whichever database production api-v3 reads (read-only) to see whether 2023-2024 is loaded there and shows the same gap.

Cross-check against api-v3: a seeded 600-bill random sample (seed 432) drawn from the local api-v3: the Chapter-action set from api-v3's actions and from the database agree on all 600 bills (137 enacted); 107 of those 137 lack the citation (78%, the full-session figure is 72%). api-v3 does not expose citations at all, so the citation side can only be read from the database.

## Why only a rescrape fills it
Washington files the chapter under the version that passed (ESSB 5167), the old scraper asked for the bare id (HB 1052) and got an HTTP 500; upstream #5876 (the OPEN-401 catch-up, OPEN-409) fixes the lookup. An incremental run does not revisit enacted bills, so nothing else fills the 494. There is no repair script on purpose: the citation comes from the legislature's own service, and a rescrape replaces the bill from source.

## Tested live before this plan (scrape only, nothing imported)
80 random bills from the 494, scraped with the catch-up Washington scraper (`os-update wa bills --scrape session=2025-2026 bill_no=...`, no database, scratch data directory, 60 requests a minute), then compared with what api-v3 stores:
* **80 of 80** now carry a `chapter` citation (with 0 "no session law data" answers).
* Actions, sponsors and vote events (223) are **identical** to the stored ones on all 80, and so are title, classification, subjects, versions, documents, sources, abstracts, other titles, other identifiers and related bills (checked field by field against api-v3); the citation is the only difference.
* Cost: 5 min 44 s and about 270 requests for 80 bills (3.4 per bill plus the bulk lists).

## Before you run (freeze the list, preflight, snapshot)
```
source activate.sh
export OPENSTATES_DB_NAME=<database being written>
./check-wa-chapter-citations.py --bill-list /tmp/wa-missing.txt                    # freeze the target list: 25 lines, 494 bills today
tr ',' '\n' < /tmp/wa-missing.txt | sort | uniq -d | wc -l                          # expect 0 (no bill listed twice)
awk '{ if (length($0) > 150) print "long line", NR }' /tmp/wa-missing.txt          # expect nothing (marker file name stays < 255 bytes)
grep -c '_status_changes' openstates-scrapers/scrapers/wa/bills.py                  # expect 1 or more: the fixed chapter lookup is the code that will run
./check-wa-chapter-citations.py --targets /tmp/wa-missing.txt --snapshot /tmp/wa-before.csv   # child-row counts of all 494, before
```
* **Pin the revision:** the lookup fix exists only in the OPEN-401 catch-up until #73 merges, so the `grep` above must pass in the checkout that runs; write fork `main`'s commit hash on the ticket.
* **Backup:** confirm the newest backup of the database being written is under a day old (the Mac's replica: `logs/db-backups/`, nightly, keep 7, restore command in RUNBOOK; production RDS: its automated snapshot). A restore would also undo everything written since, so the first remedy for a bad run is a corrected rescrape of the same list, not a restore.

## The run
```
OPENSTATES_DB_NAME=<database api-v3 serves> ./check-wa-chapter-citations.py --bill-list /tmp/wa-missing.txt   # 25 lines of 20 bills today (494)
source activate.sh
while read -r list; do ./run-scrape.sh wa "session=2025-2026 bill_no=$list" || break; done < /tmp/wa-missing.txt
```
* **Canary first (pm-review round 2):** run only the first line, then check just those 20 before the other 24 lines: `head -1 /tmp/wa-missing.txt > /tmp/wa-canary.txt; ./run-scrape.sh wa "session=2025-2026 bill_no=$(cat /tmp/wa-canary.txt)"`, then `./check-wa-chapter-citations.py --targets /tmp/wa-canary.txt --baseline /tmp/wa-before.csv --verify` (the baseline holds all 494 rows; only the listed ones are checked). Continue only if it exits 0. Any later problem is handled the same way: stop, read the listed bills, rescrape the same lines.
* **Live-test evidence added 2026-10-26** (a second 80-bill random sample, seed 9007, scrape only): 80 of 80 get exactly one `chapter` citation (0 with two), the pre-existing non-chapter citations, documents and vote events (214) are identical to what the old scraper produces, and no other field differs.
* **Why 25 short runs, not one:** `run-scrape.sh` names its marker files after the whole argument string, and one 494-bill list makes a 3,489-byte name (the limit is 255; tried: `File name too long`). Twenty bills is 177 bytes. `--chunk-size` changes it.
* **Why no `start=`:** `run-scrape.sh` takes its incremental cutoff from a marker keyed by that argument string; this one-off argument has no marker, so each run is a full-mode targeted run with no cutoff. Do not add `start=` by hand: Washington's `start=` filter (OPEN-409) skips a bill whose latest status is older than the cutoff, which is every one of these enacted bills. The live test below ran without it.
* **`|| break`:** stop at the first failed run; do not retry by hand. The list is regenerated rather than committed so it cannot go stale.
* **Rate:** `SCRAPELIB_RPM=60` (`activate.sh`). From the live test (3.4 requests a bill plus the bulk lists each run): roughly 45 minutes and 2,300 requests for all 25 runs. Washington's service is public and the 80-bill test saw no blocking.
* Run it where the catch-up scraper is live (the Mac after its 01:00 UTC pull of fork `main` once #73 has merged; Fargate only after the image deploy, which is on hold, OPEN-437). Write the fork `main` commit hash on the ticket first.

## If a run fails partway
Each run replaces only its own 20 bills and is safe to run again (the importer matches bills on their natural key and updates them). The loop stops at the first failure and the last "Starting scrape" line in `logs/scraper.log` names its list; resume from that line with `sed -n '<n>,$p' /tmp/wa-missing.txt | while read -r list; do ...; done` (the same command). Do not add `start=`.

## After
```
./check-wa-chapter-citations.py --targets /tmp/wa-missing.txt --baseline /tmp/wa-before.csv --verify
./check-wa-chapter-citations.py --verify      # whole database: 0 missing
```
**Pass:** both exit 0. The first checks every one of the 494 frozen targets directly, so a bill that lost its row or its Chapter action cannot pass by dropping out of the "missing" set: each must still exist, still carry a "Chapter N, YYYY Laws" action, carry a `chapter` citation whose number and year match that action (`Chapter N`, `WA YYYY Laws`), and have no fewer actions, sponsors, versions, documents, sources or vote events than in the snapshot. Expected: 494 targets, 494 fine, 0 problems; whole-database missing 0. Anything else: stop, read the listed bills, fix by a corrected rescrape of the same lines.
