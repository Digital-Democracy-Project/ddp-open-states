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
* Actions, sponsors and vote events (223) are **identical** to the stored ones on all 80; the citation is the only difference.
* Cost: 5 min 44 s and about 270 requests for 80 bills (3.4 per bill plus the bulk lists).

## The run
```
OPENSTATES_DB_NAME=<database api-v3 serves> ./check-wa-chapter-citations.py --bill-list /tmp/wa-missing.txt   # 25 lines of 20 bills today (494)
source activate.sh
while read -r list; do ./run-scrape.sh wa "session=2025-2026 bill_no=$list" || break; done < /tmp/wa-missing.txt
```
* **Why 25 short runs, not one:** `run-scrape.sh` names its marker files after the whole argument string, and one 494-bill list makes a 3,489-byte name (the limit is 255; tried: `File name too long`). Twenty bills is 177 bytes. `--chunk-size` changes it.
* **Why no `start=`:** `run-scrape.sh` takes its incremental cutoff from a marker keyed by that argument string; this one-off argument has no marker, so each run is a full-mode targeted run with no cutoff. Do not add `start=` by hand: Washington's `start=` filter (OPEN-409) skips a bill whose latest status is older than the cutoff, which is every one of these enacted bills. The live test below ran without it.
* **`|| break`:** stop at the first failed run; do not retry by hand. The list is regenerated rather than committed so it cannot go stale.
* **Rate:** `SCRAPELIB_RPM=60` (`activate.sh`). From the live test (3.4 requests a bill plus the bulk lists each run): roughly 45 minutes and 2,300 requests for all 25 runs. Washington's service is public and the 80-bill test saw no blocking.
* Run it where the catch-up scraper is live (the Mac after its 01:00 UTC pull of fork `main` once #73 has merged; Fargate only after the image deploy, which is on hold, OPEN-437). Write the fork `main` commit hash on the ticket first.

## After
```
./check-wa-chapter-citations.py --verify      # exit 0 = every Chapter-action bill has its citation
```
Pass: exit 0 (0 missing). Also compare bill, action and vote counts for 2025-2026 with the "before" numbers (nothing should drop; the live test found no other difference). If it fails, the bills still listed are what to look at first (`--list`); fix by a corrected rescrape of the same `bill_no=` list, not a delete.
