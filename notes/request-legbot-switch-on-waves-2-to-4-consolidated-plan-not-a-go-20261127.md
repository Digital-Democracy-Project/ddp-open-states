# REQUEST (not a GO; a plan for Ramon to decide wave by wave): **LegBot and replica routing for the live states, in waves.** 2026-11-27 ~03:00 UTC (Mac side, Onboard New States)

**Nothing here runs without a go note naming a wave.** Wave 1 (Oregon, Wyoming) is already on (your 01:50 UTC 11-26 checkpoint `11a010a`). Ramon's rules (11-25/26): waves of 2 to 3 states; **no soak: the gate is data quality**: the Stage 3 gates, a dev LegBot sample that I read and judge, and a production 100-bill sample whose summaries someone reads. Each wave is one small manifest PR (`replica_routing` and `legbot_replica` true), a rollout on EC2 and the Mac copy, the broker's state list, session rows, then the first production LegBot run.

## What each state has (dev sample read by me or my helper; replica facts; production is your reading)
| State | Dev sample (about 8 bills read) | Open items before its wave | Proposed wave |
|---|---|---|---|
| Rhode Island | **yes** (11 bills, no direction errors) | none known | **2** |
| Missouri | yes with caveats (SB 1017 is a 53-character fragment; 87 latest versions under 300 characters, none enacted) | OPEN-908 (in build), a caveat not a gate | **2** |
| North Dakota | yes with caveats (Enrollment pages carry headers and signature blocks) | OPEN-909 (not started, a caveat); OPEN-901 run is for scorecards | **2** |
| Hawaii | yes | **BROKER-615:** `onboard_jurisdiction` fails on Hawaii's 27-character session codes, so the 2024 to 2026 session rows cannot be created by the command (Broker Upgrades) | 3 |
| Mississippi | yes with caveats (PDF and HTML copies, noisy comparisons) | OPEN-899 people load and four-bill rescrape (request `8d2a2e2`); OPEN-669 live since 11-26 | 3 |
| Idaho | sample pending | OPEN-895 chain: refresh and recompute (request `a9d0c34`), then my re-sample | 3 |
| Kentucky | **no** (act versions with almost no text) | OPEN-906 (core #178 awaiting merge and an image), then refresh and re-sample | 4 |
| Maine | **no** (amendment papers stored as versions, wrong order) | OPEN-907 (in build), image, recompute; Maine's go-live (#501) is merged but not rolled out | 4 |
Scraping, not yet live (Georgia, Iowa, Montana, Oklahoma, Alabama, Nevada, Maryland) join after their go-live.

## What each wave needs (for you, after Ramon's go for that wave)
1. **Gates, read-only, report each:** nothing in flight; the starting point (`/opt/ddp-open-states` revision, the broker's `DDP_OPENSTATES_JURISDICTIONS` list); the waiver for the parity gate is Ramon's (the check no longer exists); production people counts, bills counts and the outlines for each state.
2. **Session rows** with `onboard_jurisdiction --iso2 XX --check`, `--dry-run`, then the real run (Hawaii cannot until BROKER-615).
3. **Manifest rollout** (the PR for that wave, merged first, dry run first), then api-v3 by name, the broker list (+ web, celery, beat), the drift check; the **Mac host copy is Ramon's**.
4. **The LegBot gate check** (`bill-artifact-generation` with `dry_run: true`, `limit: 1`, one bill each), as on 11-26.
5. **First production run:** a random 100-bill sample per state as for Oregon and Wyoming (same trigger and settings), **one state at a time on the Mac**, then the totals and the failed-artifact causes (`insufficient_information` is the usual one); and the read-only export of about 15 artifacts per state (as in request `7d4119e`) so I can read them. **Ramon decides whether the full session follows.**

## What I do per wave
Build the manifest PR (`/complete-ticket`), write the wave's rollout request, read the production summaries, post my verdict. I propose **wave 2 now** (Rhode Island, Missouri, North Dakota); waves 3 and 4 as their open items close.

## Not authorized
Any wave without its own go note; a scorecard switch; the policy-statement step (SYNC-184); a full-session LegBot run before the 100-bill read; any other state.

Tickets: OPEN-897 (wave 1), OPEN-665, OPEN-671, OPEN-663, OPEN-668, OPEN-669, OPEN-664, OPEN-667, OPEN-672; BROKER-615, OPEN-906, 907, 908, 909, 895; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
