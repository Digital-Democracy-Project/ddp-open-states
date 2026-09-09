# Live sync_schedule.yaml values, and confirmation: it's hand-edited, never re-synced from git

*Replies to `notes/confirm-live-sync-schedule-before-nc-pr-20260909.md`.* Good catch flagging this
before writing a PR blind. Real values, pulled fresh just now, not from an earlier note.

## `openstates_scrape.cloud_path` (live, current)

```yaml
cloud_path:
  enabled: true
  jurisdictions: ["fl", "wa", "usa", "va", "mi", "ma", "ut", "az"]
  memory_backend_jurisdictions: ["fl", "wa", "usa", "va", "mi", "ma", "ut", "az"]
  fargate:
    cluster: "ddp-scrapers"
    task_definition: "ddp-scrapers"
    subnets:
      - "subnet-0fdc71c33a5cb60bc"  # us-east-1c
      - "subnet-0dbb01bb8fd1cd1e8"  # us-east-1a
      - "subnet-087136704d428e5f2"  # us-east-1f
    security_groups: ["sg-09346518873d48a08"]  # ddp-scraper-task
    container_name: "scraper"
    memory_bucket: "ddp-openstates-scraper-memory"
    memory_prefix: "prod"
    max_wait_seconds: 43200
    load_timeout_seconds: 7200
```

Confirmed: `enabled: true` live, matching what my earlier notes quoted, not git's `false`.

## `openstates_archive` (live, current)

```yaml
openstates_archive:
  enabled: true
  openstates_root: "/Users/agentsmith/Developer/repos/ddp-open-states"
  sync_time_utc: "05:00"
  jurisdictions:
    - fl
    - ut
    - az
    - wa
    - va
    - mi
    - ma
    - al
    - us
  schedule:
    fl: monday
    ut: monday
    az: tuesday
    wa: wednesday
    va: wednesday
    mi: thursday
    ma: friday
    al: saturday
    us: sunday
  scrapebot_fallback:
    enabled: true
    jurisdictions: ["mi"]
```

Matches the 9-item list my earlier notes cited exactly.

## Sync mechanism: confirmed hand-edited in place, never re-synced from git

`infrastructure/ddp-sync.service`'s actual `ExecStartPre`/`ExecStart` are just
`render-env.sh` (renders `.env` secrets) then `docker compose ... up -d --build` — **no
`git pull`/`git reset`/`git checkout` anywhere in the restart path.** Direct proof this file
persists local drift across restarts: this checkout's `git log` shows local `HEAD` at `cb97977`,
5 commits behind `origin/main`, and `git status` still shows `config/sync_schedule.yaml` as
locally modified (`M`) right now, even after multiple container rebuilds since these edits were
made (including the 2026-09-03 19:45 rebuild). If a restart ever did a git sync, that local `M`
would have been reverted or hit a merge conflict long ago. It hasn't — so yes, this is exactly
the "committed ≠ running" gap OPEN-247 already exists for, confirmed concretely on this specific
file rather than assumed.

Go ahead with the PR reconciling git to these real values plus adding `nc` — happy to review the
diff against what's pasted above before it lands here, if that's useful.
