# Please pull the logs for the UT / NC / MI scrape failures and the MA archive timeout (read-only)

**To:** the prod agent on the EC2-broker host (`/opt/ddp-open-states`, co-located with `ddp-broker-py`).
**Why you:** this Mac has no AWS credentials, so I can't read CloudWatch or the ECS task history. The Slack
alerts below only carry ECS's generic message, which says nothing about *why* a container exited. The answer is
in the task logs on your side. Ticketing for these is not filed yet -- the logs decide what the tickets say.

**Please keep this read-only.** Do not re-trigger any of these scrapes while investigating -- in particular **not
MI** (a blind retry against a WAF makes a block worse; LESSONS.md, OPEN-53/87), and UT/NC/MI/MA all hold a
per-source S3 lock (OPEN-187), so an overlapping manual run would itself fail with "another run ... already holds
the lock". Logs and `describe-tasks` only.

## What was alerted (Slack `#automation-errors`, Agent Smith)

```
10:01 PM  OpenStates scrape failed: ut — collection exit_code_1: Essential container in task exited (after 92s)
10:02 PM  OpenStates scrape failed: nc — collection exit_code_1: Essential container in task exited (after 61s)
10:04 PM  OpenStates scrape failed: mi — collection exit_code_1: Essential container in task exited (after 273s)

 7:24 PM  OpenStates archive failed: ma — exit_code_none: gave up waiting after 43200s
          (task_arn=arn:aws:ecs:us-east-1:350941939790:task/ddp-scrapers/c1cb60eefd044e35812f205721486419);
          task stop requested (after 43210s)
```

I don't have the dates on these (the paste had times only) -- please take them from the `ddp-sync` log lines for the
same alerts, and tell me the dates you find.

## What I already know (so you don't have to re-derive it)

- "Essential container in task exited" is ECS's **generic** `stoppedReason` for a container that exited non-zero.
  It is not a diagnosis. The real reason is in the container's own stderr.
- `exit_code_1` from `cloud_collector.py` is its *catch-all failure return*. Every one of these paths returns 1:
  bad arguments, missing `MEMORY_BUCKET`, the S3 memory store unreachable, the per-source lock already held, the
  MI baseline or cookie missing, "appears unreachable" (site/WAF), an unhandled exception, or the scrape
  subprocess itself exiting non-zero. So the exit code alone can't tell these apart.
- **The three failed within minutes of each other, after 61s / 92s / 273s.** That is quick enough to suggest
  something *shared* (S3 memory store, the lock, credentials, the image, the task definition) rather than three
  independent site problems -- but I can't confirm that from here.
- **NC is new** (still `status: probing` in `jurisdictions.yaml`, only recently added to the secondary batch, and
  archiving was enabled but not on a recurring schedule). Its failure may have a different cause from UT/MI.
- **MA** is the one jurisdiction whose *full walk* alone measured ~8.2 h to scrape (LESSONS.md, OPEN-128). A
  43,200 s (12 h) ECS wait on the *archive* may simply be a legitimately slow job, or a hang -- the logs can say which.

## What to look for

The container prints exactly these lines to stderr/stdout (`cloud_collector.py`, `cloud_archiver.py`), so grep for
them in the task's CloudWatch stream (log group `/aws/ecs/ddp-scrapers`, one stream per task id under `task/ddp-scrapers/<id>`):

| If you see... | It means |
|---|---|
| `ERROR: MEMORY_BUCKET is required` | task definition / env wiring |
| `ERROR: ... -- refusing to run rather than assuming a first-ever run` (a `MemoryUnavailable`) | S3 memory store unreachable or unreadable (creds, bucket, prefix, network) |
| `ERROR: another run of <src> already holds the lock` | an earlier/overlapping task still holds the S3 lock (OPEN-187) |
| `ERROR: Michigan's last-action baseline is missing from the memory store` | MI baseline absent (OPEN-134) |
| `ERROR: no fresh published Michigan WAF cookie in the memory store` | the Mac's 6-hourly `mi_cookie_publish` hasn't published recently (retryable by design) |
| `ERROR: <src> appears unreachable` | site/WAF block (terminal; do not retry) |
| `ERROR: unhandled exception during <src> collection` + traceback | a real bug -- send me the traceback |
| `ERROR: <src> scrape failed, exit N` | the `os-update` scrape itself failed -- the lines just above it are the cause |
| `ERROR: another archive run of <src> already holds the lock` | (archive task) an overlapping archive for the same source |
| `ERROR: <src> archive failed, exit N` | (archive task) the extraction process failed -- the relayed lines just above are the cause |
| `ERROR: <src> archive exited 0 but produced no parseable summary line` | (archive task) ran but its summary line was missing |

The last JSON line is the completion record (`{"source": ..., "status": "failed", ...}`).

## Please report back, per failed task (UT, NC, MI, and the MA archive)

1. **The stopped task's `stoppedReason` and the container's `exitCode` / `reason`** (`aws ecs describe-tasks`).
2. **The last ~50 lines of the container's log stream**, plus the first `ERROR:` line and any traceback.
3. **Timestamps (UTC)** of task start/stop, so I can line them up across jurisdictions.
4. **Are all three failures the same error?** If UT, NC and MI share a first `ERROR:` line, that's the shared cause.
5. **Was another task for the same source still running when each one started?** (`list-tasks` / task history for
   the cluster `ddp-scrapers` around that time.) That would explain a lock refusal.
6. **MA archive specifically:** how many tasks were running for MA around then (was this the only one, or did the
   scrape-completion hook plus the weekly cron launch two -- OPEN-291's debounce is supposed to prevent that)?
   And what is the **last progress line** in its log -- the archive relays the extractor's output, which on the
   Mac prints lines like `ma: heartbeat, N bills processed so far` and a final `ma: N bills checked | fetched=...
   fetch_errors=...` summary -- and when was it written: progressing slowly, or silent for hours (a hang)?
7. **The `ddp-sync` log lines** for the same runs (`_run_scrape` / `cloud_scrape_trigger`), in case it recorded a
   `failure_reason` classification different from the Slack text.

## Related, already handled separately

The nightly "patch refresh -- exited 1" alert is a different problem with its own fix (OPEN-320, PR #192, deploy
request in `ddp-sync`'s `notes/ops-handoff`: `open320-request-deploy-patch-refresh-opt-out-20261005.md`). Ignore it here.

Reply on this branch with what you find (a short note is plenty -- paste the log excerpts, don't summarise them),
and I'll turn it into tickets.
