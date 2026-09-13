# OPEN-193: the other 4 ACs, checked for real against the running system

Checked each directly against this EC2 host, same standard as AC1. Results below, with real
evidence for each -- and one honest gap noted where I couldn't verify.

## 1. Cadence/eligibility/retry/backoff/failure-classification in one place -- **FALSE, found a real counter-example**

`sync_schedule.yaml` is NOT the sole source of scheduling policy on this host. `crontab -l`
shows:

```
17 * * * * /opt/ddp-broker-py/infra/scripts/refresh-openstates-people.sh >> /home/bitnami/ops/refresh-openstates-people.log 2>&1
```

This runs **hourly**, entirely outside `ddp-sync`'s own APScheduler mechanism, calling a
script that lives under `ddp-broker-py`'s own directory tree, not `ddp-sync`'s. It looks like a
legacy holdover from before `ddp-sync` existed on this host. (Side note, not this AC's concern
but worth knowing: it's been failing every single run I've observed this session --
`fatal: detected dubious ownership in repository at '/opt/openstates-people'` -- so it isn't
even accomplishing anything right now, but its mere existence as a second, uncoordinated
scheduling path is the real finding here.)

Checked systemd timers too (`systemctl list-timers`) -- nothing openstates-related, all system
maintenance (logrotate, apt, certbot, etc.). Clean on that front.

**Could not check AWS-side** (EventBridge rules, an ECS Scheduled Task, `aws scheduler`) --
this host's IAM role doesn't have `events:ListRules` or `scheduler:ListSchedules`
(`AccessDeniedException` on both, confirmed directly, not assumed). So I can only say "no
duplicate scheduling mechanism found *within reach of this host's own IAM permissions*," not
"none exists anywhere in the AWS account." Flagging this as a real verification gap, not a
clean bill of health.

## 2. Path ownership per jurisdiction in one place -- **TRUE, confirmed clean**

`_cloud_path_owns()` (`openstates_scrape.py:552`) is a pure config read:
`cloud_cfg = (config or {}).get("cloud_path", {})` against `sync_schedule.yaml`. Grepped the
whole `ddp-sync` source tree for any other jurisdiction-routing list or hardcoded
mac-vs-cloud decision -- found none. `sync_schedule.yaml`'s `cloud_path.jurisdictions` is
genuinely the one place this is decided.

## 3. Failure triage reaching Agent Smith -- **FALSE, confirmed by a real, currently-silent gap**

The code path for this exists and is real: `_alert_scrape_failure()`
(`openstates_scrape.py:105`) posts to Slack (`#automation-errors` by default) via
`SLACK_BOT_TOKEN`, plus a separate CAMS push via `CAMS_API_TOKEN`/`CAMS_BASE_URL`. **Neither is
configured on this host** -- confirmed directly against `/opt/ddp-sync/.env`: zero matches for
`SLACK_BOT_TOKEN`, `CAMS_API_TOKEN`, or `CAMS_BASE_URL`. When the token is missing, the code's
own fallback just logs a warning (`"SLACK_BOT_TOKEN not set — cannot alert on scrape failure"`)
-- nothing reaches anyone.

**This is not theoretical -- it explains MA's real 2026-09-06 failure going completely
unnoticed until I dug into it manually this week** (see
`notes/ma-2026-09-06-failure-root-cause-20260913.md`). No Slack message, no CAMS alert, nothing
in any queue Agent Smith could have polled. Whatever mechanism the plan assumed for "failure
triage reaches Agent Smith across the boundary" is not wired up with real credentials on this
host right now.

## 4. Rollback demonstrated (on-prem load against RDS) -- **Not verified as done; likely still false**

Didn't find any evidence this has been exercised for real. Consistent with an already-
established fact from earlier this session: the dev agent's Mac-side session has confirmed
zero RDS/Secrets Manager access (`AccessDenied` on `aws rds describe-db-instances`) -- which
would make an on-prem load genuinely pointed at RDS impossible as currently configured, not
just untested. I can't independently confirm the Mac's current state from this host though --
that's the dev agent's side to verify authoritatively; reporting what I can see from here
rather than assuming.

## Bottom line

AC1 and AC6 (already reported) plus AC2 here are real and solid. AC3 and AC4 are real,
currently-open gaps, not just undocumented — AC3 in particular is concerning: a real production
failure (MA) generated zero alerts to anyone this week. AC1's "one place" claim also has a real
counter-example (the legacy hourly cron), even though it's currently non-functional anyway.

Not proposing fixes for any of this right now per your instruction -- reporting real state only.
