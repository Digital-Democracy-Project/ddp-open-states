# Result 11-26 21:35 UTC: Hawaii's third re-import (OPEN-900) loaded and archived; pass numbers

## The run (`hi-5deff8cd7c36`, `hi?full=true&sessions=2026`)
* Triggered 18:44:20 UTC, 202, `full: true`, on the v98 image (`ddp-scrapers:100`). Collection done 20:51:46 (2 h 07 min); load into RDS done 21:14:09 (`cloud_scrape` 8,989 s); **the pipeline started Hawaii's archive by itself** (this run was not resumed): archive task done 21:16:12 (121 s). At the time of writing the pipeline's own `done` line has not printed yet (its post-archive follow-ups are still running and the Hawaii lock is still held). Image check: new tasks launch v98, built from scrapers `main`, which contains #297; I could not read the commit inside the image.

## Pass numbers (production RDS, read-only, after the load)
* **Bills 6,728 and vote events 12,828 in session 2026: both equal your expected numbers.** Other Hawaii sessions are empty (2023 special, 2024, 2024 special, 2025).
* **The six roll calls are `passage`, all result `fail`:** HB 1516, HB 1550 and SB 3263 ("Failed to pass Final Reading."), HB 1919 ("Failed to pass Third Reading with Representative(s) Amato, G…"), HB 2413 and SB 319 ("Failed to pass Third Reading."). A search for every roll call whose motion starts "Failed to pass Third/Final Reading" finds **exactly these six, and all six are labelled passage**.
* **Unmatched person votes: 1, "Garcia; and" (option `no`)**: the same single leftover as the second re-import's result, nothing new.
* **Not checked by me: that exactly 6 labels changed and nothing else moved.** I had no snapshot of Hawaii's labels from before this run, so I can show the end state, not the change count; you can compare with your replica. I also have not run the broker's counted-bill-chambers read (2,171 with the offline rule).

## Next
BROKER-603's Hawaii scorecard approval is Ramon's (once). Nothing was done on the broker for Hawaii, and no switch changed.
