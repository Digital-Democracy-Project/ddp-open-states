# REQUEST (not a GO): **go-live for Mississippi: a manifest rollout, dry run first** (ddp-open-states **#500**, merged, `333c2768`); **and a question about Maine's archive (no release needed).** 2026-11-26 ~04:30 UTC (Mac side, Onboard New States)

**Not a GO.** Ramon decided (recorded on OPEN-146 and OPEN-672): **Mississippi goes live now; Maine waits for its archive fix, then goes live.** He gives the go in your session naming this note.

## What I need from you
1. **Mississippi manifest rollout**, as for #494 to #496 (below).
2. **Maine's archive:** report when Maine's pipeline finishes: the archive end line and the number of archive documents saved. **No release is needed for OPEN-871:** I checked that its fix (openstates-core #173, merge `70146fac`, 11-24) is an ancestor of both `a7035d68` and v96's `4af91c90`, so the image the Fargate archive already runs contains it. Maine's replica showed 0 archive documents for 5,131 versions *before* that fix ran; the archive of the second pass is what fills it. I verify the count on the Mac replica afterwards, then build Maine's own go-live PR.

## Mississippi: what changes (read from the PR: `jurisdictions.yaml`, 10 lines, all inside `ms:`)
`status: scraping` → `live`; `enrollment.search_refresh`, `embedding`, `api_smoke_test`, `qa_sweep` false → true. **`replica_routing` and `legbot_replica` stay false.** Maine is **not** in it.

## Why it is ready (Mac replica; production is your reading)
* Second pass verified 11-26: SN 10, SN 50 and SN 101 sponsored by the "Office of the Governor" (an organization); scrapers #270 is in the image.
* **Open and small:** two roll-call voter names match no legislator ("T. (12th)", 3 votes in 2026, and "Luther-Waldo", 1 vote): OPEN-899 is being built (a people alias after looking each up in the legislature's own roll call). It is **not a blocker** for the manifest; **Ramon decides in your session whether to roll out now or after that people load.**

## Steps
1. **Gate:** #500 on `origin/main`. Read the per-state diff of the deployed copy against main and **report any state other than Mississippi that would change**; stop if so.
2. **Pull first, then the script:** `/opt/ddp-open-states` to main, then `bash deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync --dry-run` (exit 0; report its lines).
3. **On the go:** the real run, then the 11-25 checks: md5s of the checkout file, the api-v3 copy and the file inside the container equal; api-v3 healthy, no restart; drift check exit 0; `/schedule` job count unchanged (report it); ddp-sync's own read shows `live` for Mississippi. **No ddp-sync restart.** The Mac host's copy is Ramon's.
4. **Afterwards:** the first embedding and search-refresh pass for Mississippi takes hours; apply your narrow restart rule meanwhile; report the smoke test and QA sweep.

## Not authorized
`replica_routing`/`legbot_replica`; any broker switch; Maine's manifest (its own PR later); the Mac host's rollout; a ddp-sync restart; any other state. Rollback: revert the PR's lines, merge, roll out again; tell me first.

Tickets: OPEN-669 (MS), OPEN-672 (ME), OPEN-871, OPEN-899; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
