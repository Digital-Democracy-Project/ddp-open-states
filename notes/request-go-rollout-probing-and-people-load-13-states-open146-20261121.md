# REQUEST with GO: put the 13 new states at `probing` on both hosts, then load each state's people, one state at a time. No scrape. 2026-11-21 (Mac side, Onboard New States)

**Ramon, 2026-11-21 (pop-up in the onboarding session), choosing "Go: all 13, one by one":**
> make the 13 new states known on the production servers and load each state's legislators into the production database ... Each state stays at "probing", so nothing gets scraped and nothing shows on the website. Each load is checked against the expected number of people for that state; it stops on any surprise. First scrapes are not part of this.

**States (go-live tickets):**
* Wyoming (OPEN-662), North Dakota (663), Idaho (664), Rhode Island (665), Oklahoma (666), Kentucky (667), Hawaii (668);
* Mississippi (669), Montana (670), Missouri (671), Maine (672), Iowa (673), Maryland (674).

Epic OPEN-146.

**Order:** this comes after the image-follow-up work already in flight (1f1e692 step 4, ad86ad0). Don't run the rollout in part 2 while another manifest rollout or step 4's api-v3/ddp-sync deploy is running. Parts 3 and 4 need no time slot.

## What I need from you

### 1. Gates, before anything
* `/opt/ddp-open-states` must reach `origin/main` at `61d9d51` or later. That commit contains:
    * #441 (merge `6c6a49d2`), which adds 12 of the states at `status: probing` (Wyoming came earlier with #434);
    * the chamber-name and Speaker PRs #442, #444, #445, #446, #448, #449, #451, #452 and #453.
* **Check:** after `git fetch`, `origin/main:jurisdictions.yaml` has blocks `wy nd id ri ok ky hi ms mt mo me ia md`, each with `status: probing` and every enrollment flag false.
* If any block is missing or isn't `probing`, stop and report.
* `ps aux | grep run-scrape` shows nothing running on the Mac side's checkout, and no Fargate task is running for any of these 13 states. None is scheduled, so this is a formality.

### 2. Roll out the manifest on EC2
Run `bash deploy/rollout-manifest.sh --host ec2 --ddp-sync-root <ddp-sync path>`, as for New Mexico on 11-17. If the host's validator is older than main's, pull first, then run the script (OPEN-532).

**Report:**
* the commit the host now has;
* that the script exited 0 and the drift check passes (the jurisdiction count it prints);
* `/ddp/enrollment`, read from the broker's web container, lists all 13 with status `probing`;
* ddp-sync `GET /schedule` has **no** `openstates_scrape_<st>` job for any of the 13.

### 3. Pull people to main
Pull `/opt/ddp-open-states/people` to the people fork's main. That is `f9043a7abe` or later; it contains every people fix for these states, OPEN-676/678/681/690/692/697/703/716/719/723.

### 4. Load people, one state at a time
**Method:** use the container's `/opt/venv-openstates/bin/os-people`, as for NM on 11-17 (`go-nm-manifest-probing-and-people-load-open618-20261117.md`, part 3).

**For each state, in this order:** wy, nd, id, ri, ok, ky, hi, ms, mt, mo, me, ia, md.
* Run `--safe` first.
* Then run the real load, **for that state only**.

**Gate for each state:**
* **0 updated** (none of these states has ever been loaded).
* No "went missing" or retirement line.
* Created should be close to the expected count below. For NM it was 291 created against 289 expected; the 2 extra were files outside those three folders.
* **If anything is updated, or created is more than 10 away from the expected count, stop at that state and report. Don't run the next state.**

Expected counts are the files on people main `f9043a7abe`:

| State | legislature | retired | executive | **expected created** |
|---|---|---|---|---|
| wy | 93 | 166 | 3 | **262** |
| nd | 141 | 190 | 4 | **335** |
| id | 105 | 212 | 4 | **321** |
| ri | 112 | 147 | 4 | **263** |
| ok | 146 | 259 | 4 | **409** |
| ky | 138 | 200 | 4 | **342** |
| hi | 76 | 112 | 4 | **192** |
| ms | 171 | 206 | 4 | **381** |
| mt | 150 | 294 | 4 | **448** |
| mo | 188 | 408 | 4 | **600** |
| me | 188 | 430 | 3 | **621** |
| ia | 148 | 257 | 4 | **409** |
| md | 188 | 271 | 4 | **463** |

**Report per state:** the created and updated counts from both runs, and the number of current legislators read back from RDS (an open membership in the upper or lower chamber).

### 5. Read-only, please
Confirm the scrapers task-definition revision that new tasks now use. Ramon registered image v75 as `ddp-scrapers:77` and `ddp-scrapers-db:4`, and no prod note has confirmed it yet. Report the revision and the image tag the task definition points at.

## Afterwards (Mac side)
I re-read each state's people on the Mac replica and update each go-live ticket. First scrapes come later, one state at a time, each with its own request and Ramon's go.

## If something goes wrong
Stop and report. Don't retry a load. Don't hand-edit the manifest on the host. The way back for the manifest is a PR from me.

## Not authorized
* Any scrape or archive for these states.
* Moving any state past `probing`, or any enrollment flag (LegBot, routing, website).
* Any other state's people, or a people refresh of live states.
* Any image, task-definition, broker, ddp-sync or data change beyond this note.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
