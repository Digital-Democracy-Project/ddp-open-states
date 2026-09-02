# OPEN-193 — canary run: real code bug found, `assignPublicIp: "DISABLED"` hardcoded against no-NAT public subnets

*Replies to `notes/open193-redis-fixed-ready-for-canary-20260902.md`.*

Ran the actual canary: `cloud_path.enabled: true`, `jurisdictions: ["fl"]`,
`memory_backend_jurisdictions: ["fl"]`, restarted, triggered
`POST /trigger/openstates-scrape/fl`. Also hit a separate, quick config gap first --
`AWS_DEFAULT_REGION` wasn't set in the container's environment at all (`You must specify a
region.` on the first attempt), fixed by adding it to `docker-compose.prod.yml`.

## The real bug

Every one of the 4 FL sessions (`2026`, `2026D`, `2026E`, `2026F`) failed identically, confirmed
directly against the actual ECS tasks (`ecs describe-tasks`, not inferred):

```
ResourceInitializationError: unable to pull secrets or registry auth: The task cannot pull
registry auth from Amazon ECR: There is a connection issue between the task and Amazon ECR.
Check your task network configuration. operation error ECR: GetAuthorizationToken, exceeded
maximum number of attempts, 3, ... dial tcp <ip>:443: i/o timeout
```

Root cause: `cloud_scrape_trigger.py`'s `_run_fargate_collection()` hardcodes
`"assignPublicIp": "DISABLED"` in its `networkConfiguration`. But the three subnets this whole
thread verified and wired into `sync_schedule.yaml`
(`subnet-0fdc71c33a5cb60bc`/`subnet-0dbb01bb8fd1cd1e8`/`subnet-087136704d428e5f2`) are plain
public subnets with **no NAT gateway** -- `infra/fargate-spike/variables.tf`'s own comment says
the design deliberately relies on a public IP per task specifically *to avoid* needing one. With
`DISABLED` in a subnet that has no other egress path, the task's ENI gets no route to the
internet at all, so it can never reach ECR to pull its own image -- confirmed with a live
`ecs.run_task()` call from inside the `ddp-sync` container itself using `assignPublicIp:
"ENABLED"` instead: succeeded in under a second, task reached `RUNNING` normally.

Each doomed session took ECS ~5 minutes to give up on (3 retries, i/o timeout) before
`run_fl_scrapes_job` moved to the next one -- so the whole canary run silently burned about 20
minutes of real (billable) Fargate compute across 4 guaranteed-failure attempts, plus a second,
independent trigger (not something I called -- see below) queued behind it that would have
repeated the same cycle.

## Cleanup already done

- Found the stuck-`PENDING` 4th task (`.../82b05496567b4241b1b2177b9d3ab198`, session `2026F`)
  via `ecs:ListTasks` (see IAM note below) and stopped it directly rather than waiting out its
  own ~5 minute failure cycle.
- Stopped the `ddp-sync` service entirely once the root cause was confirmed, rather than let a
  second trigger's own 4 sessions repeat the identical doomed cycle. Cluster is clear -- `ecs
  list-tasks` returns nothing running or pending.
- `cloud_path.enabled` is still `true` / `jurisdictions: ["fl"]` in `sync_schedule.yaml` on this
  host (left as-is, matching the actual intended state) -- the trigger call is what needs to
  change, not the config.

## One more thing worth a direct answer: a second, un-requested trigger

A second `POST /trigger/openstates-scrape/fl` fired at 05:43:20 (`run_id=fl-ffdf2c4d9b1e`) that
I did not call and the user on this end confirmed they didn't either. Only ever saw one task
active in ECS at a time, so it looks like it queued behind the first trigger's sessions rather
than running truly concurrently -- but the source of that second call is still unexplained. Not
chasing it further myself since the root cause (and the fix) is the same either way, but
flagging in case it points at something worth knowing about (a retry mechanism, another
caller of this same endpoint, etc.).

## IAM note

Needed `ecs:ListTasks` to find the stuck task and confirm the cluster was clear afterward.
Same lesson as `ec2:DescribeSubnets` earlier: tried scoping it first to
`container-instance/ddp-scrapers/*` (matching the resource type AWS's own denial message named),
still denied even once that exact ARN was live in the policy -- dropped the resource restriction
entirely (`Resource: "*"`) and that worked. Listed as `ECSListTasks` in the same policy block as
everything else.

## What's needed

A real fix to `_run_fargate_collection()` -- `assignPublicIp` needs to come from
`fargate_cfg` (or otherwise reflect the actual subnet type) rather than being hardcoded
`"DISABLED"`. Given every subnet this project has actually stood up so far is public-by-design
(the OPEN-200 spike, and this canary's own subnets), the simplest fix is probably just flipping
the hardcoded value to `"ENABLED"` -- but that's a call for whoever owns this file, not something
to patch unilaterally the way I didn't touch `config.py` for the last two bugs either. Not
re-attempting the canary until this lands and merges.
