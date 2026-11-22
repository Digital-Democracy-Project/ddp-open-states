# UPDATE to `d4fa3f5` (the next scrapers image after v75): it now also carries BROKER-564 (Maine) and OPEN-745 (Iowa). Scrapers main is `0d211c96`. 2026-11-21 (Mac side, State Specific Handling)

**Not a GO.** Everything in `d4fa3f5` stands: OPEN-644 Alabama #195, OPEN-645 Massachusetts #197 (with the watch on the first full Massachusetts run, about +5 h), and OPEN-744 Iowa #196. Core is unchanged at `7f531958`.

## Added since `d4fa3f5` (scrapers main now `0d211c96bdcf9dc7b66ddb15dbd411d2a812ec93`)
| Merge | What |
|---|---|
| #198 (OPEN-745, `31b480c3`, from the Onboard New States session) | Iowa special sessions. Iowa is onboarding and not scheduled |
| #199 (BROKER-564, `0d211c96`) | Maine marks its "Ought Not to Pass" roll calls with `ddp_yes_is_against`: a YES on them is a vote against the bill (Ramon, OPEN-698). Maine is not live and not scheduled, so nothing is written until Maine's own scrape |

## BROKER-564 is two halves
* **The broker half is ddp-broker-py #801** (`14927972`, migration `0109_motion_yes_is_against`), merged and not deployed. It is a broker release, through `/broker-deploy` in a ddp-broker-py session, not this image.
* **Either order is safe:**
  * this image without the broker: the flag is stored in the vote's extras and ignored;
  * the broker without this image: the new column stays False.
* **Both must be live before any Maine vote counts** (OPEN-672, Maine go-live).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
