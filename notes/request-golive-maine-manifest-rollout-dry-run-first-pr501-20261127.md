# REQUEST (not a GO): **go-live for Maine: a manifest rollout, dry run first** (ddp-open-states **#501**, head `d261aadfce129461ae552d783621f426a06e41d2`, CI green, **not merged yet**). 2026-11-27 ~01:20 UTC (Mac side, Onboard New States)

**Not a GO.** Ramon decided (OPEN-672, 11-26): Maine waits for its archive, then goes live. The archive is filled: your 05:55 checkpoint (`fa843bb`) read 5,131 versions archived with 0 errors, and I counted **5,131 Maine archive documents, all with text, on the Mac replica**. He gives the go in your session naming this note. **This request starts only after the PM has merged #501** (you will see it on `origin/main`).

## What changes (read from the PR: `jurisdictions.yaml`, 10 lines, all inside `me:`)
`status: scraping` → `live`; `enrollment.search_refresh`, `embedding`, `api_smoke_test`, `qa_sweep` false → true. **`replica_routing` and `legbot_replica` stay false.** Maine's open items are not in this request (OPEN-866 relabel and recompute, OPEN-850, scorecard rules, dev LegBot sample).

## Steps (as for #494 to #500)
1. **Gate:** #501 is on `origin/main`. Read the per-state diff of the deployed copy against main; **report any state other than Maine that would change**; stop if so.
2. **Pull first, then the script:** `/opt/ddp-open-states` to main, then `bash deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync --dry-run` (exit 0; report its lines).
3. **On the go:** the real run, then the checks: md5s of the checkout file, the api-v3 copy and the file inside the container equal; api-v3 healthy, no restart; drift check exit 0; `/schedule` job count unchanged; ddp-sync's own read shows `live` for Maine. **No ddp-sync restart.** The Mac host's copy is Ramon's.
4. **Afterwards:** the first embedding and search-refresh pass for Maine (2,450 bills) takes hours; apply your narrow restart rule meanwhile; report the smoke test and QA sweep.

## Not authorized
`replica_routing`/`legbot_replica`; any broker switch; the Mac host's rollout; a ddp-sync restart; any other state. Rollback: revert the PR's lines, merge, roll out again; tell me first.

Tickets: OPEN-672 (ME), OPEN-871; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
