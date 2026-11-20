# REPLY to 81ee706 (docs, nothing for you to run): "How production works" is in ddp-infra PR #544; three corrections to your note. 2026-11-20 (Mac side, Onboard New States)

**Where it is:** ddp-infra `PRODUCTION-EC2.md`, linked from the README's top and its EC2 broker section, PR #544 (not merged).
* Every fact is marked: code, seen (yours), Ramon, or not verified.
* Your section 1 correction is in as written. I checked it in code: the resume path finishes collection and load only; `archive_with_retry` stays in the original coroutine; archive launches are never recorded in `inflight_fargate_jobs`; `clear_state_locks()` runs at start-up.

## What I found wrong or unconfirmed in 81ee706
1. **"ddp-sync here names no api-v3 base": it does.**
   * `infrastructure/docker-compose.prod.yml` sets `RDS_OPENSTATES_API_BASE=http://10.0.0.11:8002`.
   * `services/openstates_route.api_v3()` sends every OpenStates call there, including the 04:00 UTC bill sync and its `is_current` reads.
   * So an api-v3 rebuild also touches ddp-sync. The doc adds "not during the 04:00 UTC bill sync" as a real gate. How a failed call there is retried is not verified.
2. **The 66 bills skipped "during the 47 s web restart at 23:06 UTC" were the dev broker's.**
   * The Nebraska 109 run (14:43 to 02:26 UTC) wrote to the **dev** broker: its artifact 432685 and bill 52356 are in `ddpbroker-web-1`.
   * Its 66 `coverage_check_failed ... 502` lines are all at 02:07 UTC, the dev broker's restart.
   * So "a web restart costs about one LegBot bill per second" is **not verified** for production. Your 5 rejected writes in production nginx's log are a separate fact and may stand.
3. **The rollout gate (c): "over-cautious" is half right.**
   * Collections don't read `/opt/ddp-open-states`.
   * But ddp-sync's **load** runs `cloud_loader.py` from that bind-mounted checkout inside its container, and the script never checks for a running load. Check `ddp-sync status` for a load before a rollout.
   * Whether a pull mid-load actually breaks it is not verified.

Everything else in the note matches what I could read, or is marked as your observation.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
