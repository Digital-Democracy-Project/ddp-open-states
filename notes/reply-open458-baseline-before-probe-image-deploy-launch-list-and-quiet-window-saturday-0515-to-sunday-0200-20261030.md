# Reply (read-only) for OPEN-458: baseline before the probe image deploy. Nothing running now; the longest quiet window is Saturday 10-31 about 05:15 to Sunday 11-01 02:00 UTC (about 20 h 45 min)

Prod agent, Fri 2026-10-30 18:25 UTC. The operator said "Option A, run all three reads". Read-only: ddp-sync's schedule and in-flight record, SELECTs against the RDS, listings of the memory bucket; nothing launched, pulled, built, restarted or written. Output in `/home/bitnami/ops/open458-baseline-20261030T1814Z/` (`schedule-raw.txt`, `baseline.txt`). Read at 18:15 to 18:17 UTC.

## 1. Launches due until Monday 11-02 00:00 UTC (this host's ddp-sync live scheduler)
**Running or queued now: nothing.** The in-flight Fargate record is empty, ddp-sync had no activity in 15 minutes, no broker write in 10, no api-v3 request in 10; **no state is escalated to nightly** (all nine cadence keys absent; the 10-30 00:30 review: all seven states weekly, `changed=0`). Nothing more is due tonight (Fri 10-30): the daily jobs have all run (WA 02:35, USA 03:00 to 04:31, MA archive 05:02 today).
| UTC | what | notes |
|---|---|---|
| Sat 10-31 00:30 | cadence review | launches nothing itself |
| Sat 02:30 | **WA scrape** (daily) | about 5.5 min, then its archive about 1.5 min |
| Sat 03:00 | **USA scrape**, lower then upper (daily); people pull | the chain took 03:00 to 04:31 today (two scrapes, two archives of about 12 min) |
| Sat 05:00 | **archive AL** | only Saturday archive (AL is `paused` in the manifest; the job is scheduled anyway; duration unknown) |
| Sat 06:20 | jurisdiction drift check | no launch |
| Sun 11-01 00:30 | cadence review | |
| **Sun 02:00** | **FL scrape (all sessions) and the weekly secondary batch: VA, MI, MA, UT, AZ, NC** | each followed by its scrape-triggered archive; MA's scrape alone took about 10 h last Sunday (its last write was 10-25 12:21) |
| Sun 02:30 | WA scrape (daily) | |
| Sun 03:00 | USA scrape (daily); people pull | |
| Sun 05:00 | archive US | |
| Sun 07:00 | GrantBot (monthly, the 1st) | not an OpenStates launch |
| Sun 10:00 | people refresh | database, not a scrape task |
Not in the window: Monday 05:00 archives FL and UT (after 00:00 Monday); Tue AZ, Wed VA and WA, Thu MI and NC, Fri MA. I read only **this host's** scheduler; the Mac's own jobs are not covered.

## 2. The baseline (same script and fields as the 10-27 one; nothing skipped except the live task-definition revision, which this role cannot read)
| State | bills | vote events | person votes | change since 10-27 |
|---|---|---|---|---|
| Virginia | 4,396 | 11,553 | 452,159 | none |
| Arizona | 2,190 | **3,411** | 75,720 | vote events 3,443 to 3,411 (my 10-28 24-bill rerun deleted 32 stale empty events) |
| Washington | 3,411 | 2,302 | 171,556 | none |
| Florida | 7,685 | 10,228 | 324,838 | none |
| Michigan | 4,159 | 1,279 | 96,376 | none |
| USA | **39,097** | 1,604 | 561,033 | bills 39,084 to 39,097 |
| Utah | 1,021 | 1,917 | 93,865 | none |
| Massachusetts | 11,840 | 529 | 46,448 | none |
| North Carolina | 2,343 | 781 | 72,680 | none |
* Virginia: passage motion rows **4,165** (2026: 4,136; 2026S1: 29); motion text starting `H VOTE:` **2,188**. Duplicate vote-event groups: **Arizona 247** (249 before the rerun), Massachusetts 32, Virginia 290, Washington 1 (the rest none). Florida committee votes with no person votes: **0**.
* **Newest working-tier run per state** (by last write; objects, bytes): va `va-14bad9d7e58c` 10-25 (13, 27,933); **az `az-ab95b8d4bd4a` 10-28 01:29 (62, 354,045): this is my 24-bill targeted rerun, not an incremental run; the newest incremental Arizona run is the 10-27 canary `az-0f32cd69beb3`**; wa `wa-373b9d1d59de` 10-30 02:35 (1, 60: manifest only); fl `fl-68e84cc45b3d` 10-26 (1, 60); mi `mi-b98df4482eaf` 10-25 (13, 30,396); usa `usa-53e8e53cd238` 10-30 04:17 (21, 207,513); ut `ut-7902ffd91496` 10-25 (5, 10,659); ma `ma-0c34a47aae70` 10-25 12:21 (12,261, 43,369,992); nc `nc-c1e6ba36f200` 10-25 (3,129, 19,155,397). (A `working-tier/co/` folder also exists now from the Colorado probe.)

## 3. A quiet window
* **Longest gap with no launch due: Saturday 10-31 about 05:15 UTC to Sunday 11-01 02:00 UTC, about 20 h 45 min** (the Sat 05:00 AL archive is the last launch; I assumed it ends within about 15 minutes; its duration is unknown). The next gap is the one now: **Fri 10-30 18:15 to Sat 10-31 02:30 UTC, about 8 h 15 min** (nothing due; the first launch is WA).
* Sunday 02:00 starts the weekly batch, which runs for hours, and the daily WA and USA jobs overlap it, so there is no quiet time on Sunday morning. For a canary by hand (an Arizona incremental run took about 82 min on 10-27) the Saturday window leaves room: register by about midday Saturday, canary by about 14:00, well before Sunday 02:00.
* I do not know whether a task already running when a new revision is registered keeps the old one (each launch names the family and takes the latest ACTIVE revision at launch time); nothing should be running Saturday in that window, which avoids the question.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
