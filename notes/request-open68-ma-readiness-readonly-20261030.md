# Request (read-only): is Massachusetts (MA) ready to be served from our own database?

2026-10-30. Ramon decided on 10-29 that MA is one of our supported states and should be served from our own database (OPEN-68). **Nothing here changes anything: no pull, no restart, no recreate, no edit, no flag, and nothing is added to the broker's list.** Please do not print secrets (counts, lists and times only).

## Why
Your 10-30 00:00 UTC read showed the one drift the check flags is MA: ddp-sync's list has it, the manifest's `replica_routing` and the broker's `DDP_OPENSTATES_JURISDICTIONS` (`MI,UT,US,VA,AZ,WA,FL,NC`) do not. Before the manifest changes and before the broker's list gets MA, someone has to read whether MA's data is really there. The flip changes what the public sees, so it waits for this answer. NC's flip was held on the same kind of check (BROKER-302: the replica had 0 NC legislators against 173 public).

## Please read and answer (for MA only)
1. **People.** In the database the production broker reads for `DDP_OPENSTATES_JURISDICTIONS` states: how many current MA legislators, split by chamber? Public OpenStates has 200 (160 House, 40 Senate) as far as I know; please say the number you read and which database it came from.
2. **Bills and sessions.** The MA legislative sessions present, and the bill count in the current session, beside the public OpenStates count if you can read it without a write.
3. **Roll calls with no voters.** How many MA vote events have a tally but no recorded voters (OPEN-176 says 152 on the Mac copy)? Same query on the production database. Also: how many MA vote events in total?
4. **Committees.** How many MA committees and committee memberships exist (OPEN-68 notes a July committee/people gap)?
5. **Any other state-level check you already run for a new state** (the NC parity gate in BROKER-302 is the model): report its result for MA, or say it cannot run read-only.

## What I will do with the answer
Record it on OPEN-68 and OPEN-318. If MA is ready, the next steps are a manifest PR (MA `replica_routing` to yes) and a separate request asking you to add MA to the broker's list; if not, the gaps become tickets. Nothing changes in production on this request.

## Not asked
Whether the Slack drift message was sent on 10-29, and the drift finding on each run (the 10-28 note says the EC2 host lacked the LegBot replica list, your 10-30 note says MA); if you have the raw drift lines for both runs, please quote them verbatim.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
