# REQUEST (not a GO): **go-live for Alabama: a manifest rollout, dry run first.** The change is ddp-open-states **#513**, **merged** (merge `4c78d958`, head `a353f63a`, CI `validate` green). 2026-11-27 (Mac side, Onboard New States)

**Not a GO.** Ramon gives the go in your session naming this note; please confirm it with him. Alabama's gates were re-run on the Mac replica after the 11-25 re-import (Stage 3 structural passes, govbot check 0 failures, motion rules, versions 0 of 2,867 unstaged, archive 2,923 documents with 0 errors); the evidence is on OPEN-523.

## What changes (read from the PR: `jurisdictions.yaml` only, the `al:` block)
`status: scraping` to `live`; `enrollment.search_refresh`, `embedding` and `api_smoke_test` false to true (`qa_sweep` was already true). **`legbot_replica` stays false** (separate LegBot switch-on), and `replica_routing` is already true since #505.

## The steps
1. **Gate:** `origin/main` of ddp-open-states is at `4c78d958` **or newer** and contains #513. Read the per-state diff of the deployed copy against main and **report any state other than AL that would change** (the ND `clean_nd_text` flip from #511 may show if not yet rolled out: say so; do not stop for it, but tell me). Stop if anything else differs.
2. **Pull first, then the script**, on **each host that holds a manifest copy** (EC2, and the Mac host's copy is Ramon's step: tell me who runs it): `bash deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync --dry-run` (must exit 0; report its lines).
3. **On the go:** the real run, then the checks as for the earlier rollouts: md5 of the checkout file, api-v3 copy and the file in the container equal; api-v3 healthy, no restart; drift check exit 0 (report it); `/schedule` job count unchanged (report it); ddp-sync's own read shows `live` for Alabama. **No ddp-sync restart.**
4. **Afterwards:** the first embedding and search-refresh pass for Alabama runs for hours in ddp-sync's process; apply your narrow restart rule meanwhile, post when it finishes, and report smoke test and QA sweep results.

## Separate steps (not part of this request)
**VoteBot's state list** (VoteBot owner) and the **LegBot switch-on** (`legbot_replica`, a later wave) are separate steps; do nothing about either here. The readiness check for Alabama is requested in its own read-only note in ddp-broker-py.

## Not authorized
`legbot_replica`; any broker switch; any other state; a ddp-sync restart; a scrape or re-import. Rollback: revert the PR's lines, merge, roll out again; tell me first.

Tickets: OPEN-523; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
