# OPEN-129: does a scrape-failure alert actually reach a human? (2026-08-22)

Verification-only investigation. **The delivery path works.** Both implementations were fired
against production and both landed. The reason the AZ/UT staleness alerts went unacted-on for four
days is not delivery — it is triage, and the mechanism is structural rather than a judgement lapse.

## Why this was asked

`PLAN-incremental-scraping.md` deferred this twice, conditionally (~line 1760 "deferred to
post-merge, per PR #15's test plan"; ~line 1789 "production `SLACK_BOT_TOKEN`/`CAMS_API_TOKEN`/
`CAMS_BASE_URL` verification"). Both conditions had since fired — PR #15 is merged and `ddp-sync`
has been up since 2026-08-21 — and nobody had picked it back up. Meanwhile SYNC-35 recorded AZ
sitting stale for 14 days with the watchdog's sentinel files still present four days after alerting,
which read like a delivery failure.

Four other tickets propose *adding* callers to this path (OPEN-87's `SUPPRESS_FAILURE_ALERT`
design, OPEN-127, SYNC-2, SYNC-35), so confirming it works was a prerequisite rather than a
nice-to-have.

## Config: both tokens are live, despite one looking absent

| Variable | `ddp-agents/.env` | `ddp-sync/.env` | live `ddp-sync` process |
|---|---|---|---|
| `SLACK_BOT_TOKEN` | set (58 ch, `xoxb-`) | **absent** | **set** (58 ch, `xoxb-`) |
| `CAMS_API_TOKEN` | set (64 ch) | set (64 ch) | **set** (64 ch) |
| `CAMS_BASE_URL` | absent | absent | absent — defaults to `http://localhost:8000` |
| `HEALTH_ALERT_SLACK_CHANNEL` | absent | absent | absent — defaults to `#automation-errors` |

Checked via `ps eww` on the running uvicorn process, not by reading `.env` alone. That distinction
matters: `_alert_scrape_failure` reads `os.getenv`, and `ddp-sync/.env` has no `SLACK_BOT_TOKEN`, so
a `.env`-only check would have wrongly concluded Slack alerting was dead. The daemon gets it from
elsewhere (launchd plist or wrapper). Both defaults are correct, so neither missing variable is a
problem.

## Both delivery paths fired successfully

**1. `ddp-sync`'s Python path** — `_alert_scrape_failure()` invoked directly with the live process's
own environment:

```
POST https://slack.com/api/chat.postMessage   -> 200
POST http://localhost:8000/api/v1/failures    -> 202
```

Slack returns 200 even for `{"ok": false}`, so this was confirmed independently by reading the
channel: the message is present at 2026-08-22 21:56:11 EDT.

**2. `run-scrape.sh`'s bash path** — a separate implementation with its own token extraction and
hand-built JSON, so it was exercised separately. Token extraction via the script's own `grep`/`cut`/
`tr`/`awk` pipeline yields the correct 58- and 64-character tokens. Replicating
`report_failure_to_cams()` exactly:

```
POST http://localhost:8000/api/v1/failures    -> 202
{"status":"triaging","fingerprint":"7aad7d43ae7c92a0","repo":"ddp-open-states"}
```

Slack was deliberately not re-fired from the bash path — it uses the same token, channel literal and
endpoint already proven above, and the channel is noisy enough without a second test post.

`/api/v1/failures` is POST-only (`GET` returns 405), so the record cannot be read back through it;
the `202` plus the `triaging` fingerprint is the delivery evidence.

## The actual finding: staleness alerts are structurally always declined

The alerts arrived. They were also picked up by CodeBot's failure listener, evaluated, and
**explicitly declined** — three times out of three, each for the same stated reason:

| When | Alert | CodeBot decision and reason |
|---|---|---|
| 2026-08-08 19:57 | `mi` stale, 333h (46% over threshold) | No ticket — *"no stacktrace or error evidence of a code defect"* |
| 2026-08-18 11:02 | `ut` stale, 229h (0.4% over) | No ticket — *"marginal… just 1 hour over… no stacktrace or code-level error"* |
| 2026-08-18 12:32 | `az` stale, 229h (0.4% over) | No ticket — *"marginal… ~0.4% over… no stacktrace or scraper error"* |

Two things follow, and the second is the important one.

**The "marginal" reasoning is an artifact of when the alert fires.** `check-scrape-staleness.sh`
alerts the first time a job crosses its threshold, so the first (and, per the sentinel de-dupe, only)
alert always reports a value barely over the line. 229h against a 228h threshold genuinely reads
like a rounding error. It is not: the underlying condition then grew to **14 days** with no further
alert, because `az.stale-alerted` correctly suppresses repeats for the same episode. The alert is
emitted at exactly the moment it looks least serious, and the de-dupe guarantees it never looks
worse later.

**But the deeper reason is a category mismatch, not a judgement call.** MI's alert was 46% over
threshold, not 0.4%, and was declined too — with the same "no stacktrace" reasoning. Staleness is the
*absence* of activity. It can never present a stacktrace or a scraper error, so a triage rule that
requires code-level evidence will decline every staleness alert it ever sees, regardless of severity.
CodeBot behaved reasonably within its own rule; the rule cannot represent this class of failure.

This is a close cousin of SYNC-3, where a sustained-WAF-block escalation has never once fired
because its classifier reads a stream the detail never reaches. Same shape: monitoring that exists,
is wired, and cannot succeed.

## Secondary finding: the channel is noisy

`#automation-errors` carries a Zapier failure (`MOB Form Federal Bill pipeline` — *"The app returned
'No such Bill.'"*) repeating every roughly 20–40 minutes, all day. Five of the six most recent
messages before this test were that same error. Even a correctly-delivered, correctly-triaged alert
has to compete with that for a human's attention.

## What this closes and what it does not

**Closed:** delivery works, on both paths, with real tokens, verified by receipt rather than by exit
code. Anything built on top of `_alert_scrape_failure` (OPEN-87, OPEN-127, SYNC-2, SYNC-35) can
assume the transport is sound.

**Not closed, and now better understood:** nothing turns a real, growing staleness into something a
human or CodeBot will act on. Filed separately — see the ticket link on OPEN-129. The fix is not
more alerting; it is escalation on an existing alert (re-alert as the multiple grows) and a triage
path that can accept an absence of activity as evidence.

## Reproducing

```sh
# live process env, presence and length only -- never print the values
ps eww <ddp-sync-pid> | tr ' ' '\n' | grep -E '^(SLACK_BOT_TOKEN|CAMS_API_TOKEN)='

# python path
cd ddp-sync && PYTHONPATH=$PWD/src .venv/bin/python -c \
  "from ddp_sync.pipelines.openstates_scrape import _alert_scrape_failure; \
   _alert_scrape_failure('TEST', 'ignore', 1.0)"
```

Mark any test alert unmistakably as a test in its label — it lands in a channel real people read.
