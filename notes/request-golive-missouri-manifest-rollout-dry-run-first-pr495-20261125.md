# REQUEST (not a GO): **go-live for Missouri: a manifest rollout, dry run first.** The change is ddp-open-states **#495** (head `de6b5e21f265d77aab7deb7a19d7ef721d83a2a8`, CI green, **not merged yet**). It can go in the same rollout as the four states of `request-golive-hawaii-rhode-island-north-dakota-kentucky-…-pr494-…` (#494 is already merged), or on its own. 2026-11-25 ~22:40 UTC (Mac side, Onboard New States)

**Not a GO.** Ramon decided (11-25, recorded on OPEN-146, via the PM) that Missouri goes live **after its version-comparison cleanup is committed**: that cleanup is **done** (your `508bef1`). **He gives the go in your session naming this note;** please confirm it with him. **This request starts only after the PM has merged #495** (you will see it on `origin/main`).

## What changes (read from the PR: `jurisdictions.yaml` only, 10 lines, all inside the `mo:` block)
`status: scraping` → `live`, and `enrollment.search_refresh`, `embedding`, `api_smoke_test`, `qa_sweep` false → true (exactly what #494 did for the four states and #480 for New Mexico). **`replica_routing` and `legbot_replica` stay false** (not named by the decision; Ramon's separate call).

## Why it is ready (Mac replica, today; production is your reading)
* Re-import verified (11-24): **3,161 bills**, SB 1470 present and signed, the 28 missing Senate bills present, **0 unmatched of 80,427** person votes.
* Archive: `fetched=47 archived=47`, 0 errors (your 22:09 note).
* **The comparison cleanup is committed and verified:** your commit (corrected 461, nulled 598, flags changed 746) and my re-run of the dry run at 22:12 UTC reads **0 pending**.

## The steps (as in the four-state request)
1. **Gate:** #495 is on `origin/main`. Read the **per-state diff of the deployed copy against main** and **report any state other than Missouri (and the four #494 states, if they are not yet rolled out) that would change**; stop if so.
2. **Pull first, then the script:** `/opt/ddp-open-states` to main, then **`bash deploy/rollout-manifest.sh --host ec2 --ddp-sync-root /opt/ddp-sync --dry-run`** (must exit 0; report its lines; `--state mo` prints Missouri's values).
3. **On the go: the real run** (same command without `--dry-run`), then the checks as on 11-25: the md5 of the checkout file, the api-v3 copy and the file inside the container equal; api-v3 healthy, no restart; drift check exit 0; `/schedule` 35 jobs; ddp-sync's own read shows `status live` for Missouri. **No ddp-sync restart.** The Mac host's copy is not part of this request.
4. **Afterwards:** the first embedding and search-refresh pass for Missouri (3,161 bills) takes hours in ddp-sync's process; apply your narrow restart rule meanwhile and post when it finishes, and report the smoke test and QA sweep results by state.

## Not authorized
`replica_routing` or `legbot_replica`; any broker switch (the scorecard switch comes later, BROKER-491); the Mac host's rollout; a ddp-sync restart; any state other than those named. Rollback: revert the PR's 10 lines, merge, roll out again; tell me first.

Tickets: OPEN-671 (MO); OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
