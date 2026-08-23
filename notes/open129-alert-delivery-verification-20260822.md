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

## What is and is not verified here

Worth being precise, because four other tickets depend on this answer and could over-read it:

- **Verified:** a Slack message reaches `#automation-errors` (observed in the channel, not inferred
  from a 200). CAMS *accepts* the POST and enters triage (202 + a `triaging` fingerprint).
- **Verified:** both token-extraction implementations produce working credentials against production.
- **NOT verified:** durable CAMS persistence or readback — the endpoint is POST-only, so there is no
  way to fetch the record back. The fingerprint is an intake receipt, not proof of storage.
- **NOT verified:** that an alert becomes a human-actionable item. It demonstrably does not, today —
  see below.
- **NOT a licence to add callers.** This says the transport works. Any new caller still needs its own
  justification and alert semantics.

## The actual finding: triage declines these, and it is predictable rather than accidental

The alerts arrived. They were also picked up by CodeBot's failure listener, evaluated, and
**explicitly declined** — three times out of three, each for the same stated reason:

| When | Alert | CodeBot decision and reason |
|---|---|---|
| 2026-08-08 19:57 | `mi` stale, 333h (46% over threshold) | No ticket — *"no stacktrace or error evidence of a code defect"* |
| 2026-08-18 11:02 | `ut` stale, 229h (0.4% over) | No ticket — *"marginal… just 1 hour over… no stacktrace or code-level error"* |
| 2026-08-18 12:32 | `az` stale, 229h (0.4% over) | No ticket — *"marginal… ~0.4% over… no stacktrace or scraper error"* |

**First read, which was wrong and is worth recording as such.** My initial conclusion was that a
triage rule *requires* a stacktrace, and therefore declines every staleness alert structurally. A
reviewer pushed back that three declines don't prove a rule, so I read the rule instead of inferring
it — `ddp-agents/src/agent_smith/failure_watcher.py:130-150`. There is no such rule:

> "…transient / external / expected — a DB connection drop, an out-of-memory, a network blip, an
> auth/config value that's just unset, **a normal empty result (e.g. a scraper that returns little
> because the legislature is out of session)**. Use your knowledge of the service; **there is
> deliberately no hardcoded rule list**."
>
> "Be conservative: a wrong ticket wastes CodeBot and a human reviewer. **When genuinely unsure
> whether it's a bug vs. expected behavior, decline and say why.**"

**The accurate finding is narrower and more actionable.** Triage is an LLM judgement with a
deliberate conservative bias, and the alert gives it almost nothing to judge on:

1. The prompt's own list of *expected* conditions includes a scraper being quiet because the
   legislature is out of session. A staleness alert is close to indistinguishable from that, on the
   information it carries.
2. `stacktrace` is genuinely empty for these — the prompt renders it as `(none provided)` — so the
   only signal is one line: `scrape staleness: az last run 229h, threshold 228h`.
3. Given "when unsure, decline," declining is the *designed* response to that input. Both declines
   even reasoned about marginality (229h vs 228h) and got it right on the numbers.

So this is not a broken rule and not a bad decision. It is an alert that does not carry enough to
distinguish "quiet because out of session" from "this job is dead," handed to a system explicitly
told to decline when it cannot tell.

**Two compounding factors that make it worse than a single bad call.** `check-scrape-staleness.sh`
alerts on first threshold crossing, so its one and only alert always reports a value barely over the
line — 229h against 228h reads as a rounding error, and it *is* marginal at that instant. The
condition then grew to **14 days** with no further alert, because `az.stale-alerted` correctly
suppresses repeats for the same episode. The alert fires at the moment it looks least serious and, by
design, never looks worse later. And MI's 2026-08-08 alert was 46% over threshold, so severity alone
does not rescue it either.

The fix therefore belongs in the alert, not the triage engine: say "this job has produced no
successful run in N days across M scheduled attempts" rather than "229h vs a 228h threshold," and
re-alert as the multiple grows. That is a separate ticket, deliberately not built here.

Related in shape, though not in mechanism: SYNC-3's sustained-WAF-block escalation has never once
fired because its classifier reads a stream the detail never reaches. Both are monitoring that is
wired up and still cannot do its job.

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

## Live-test hygiene

This investigation posted a real message to a channel real people read, and a real record to CAMS.
For the record:

- Operator authorisation was obtained in advance, specifically for forcing a real failure alert.
- Both were labelled unmistakably as tests — `OPEN-129 DELIVERY TEST (not a real failure)` and
  `AlertDeliveryVerification` / *"deliberate test of run-scrape.sh's bash CAMS path - ignore"*.
- Slack was fired **once**, from the Python path only. The bash path's Slack call was *inspected*
  rather than fired — it builds its JSON inline with shell interpolation (`run-scrape.sh:64-69`)
  rather than via `json.dumps`, so it is a genuinely different construction, but it uses the same
  token, the same hardcoded `#automation-errors` literal and the same endpoint, all already proven.
  A second post was judged not worth the channel noise. If someone wants that exact payload proven,
  it remains unfired.
- Checked afterwards for unintended side effects: **no Jira issue was created** in the 30 minutes
  following either POST, so CodeBot's triage did not turn the test into a ticket.
- The CAMS test record cannot be deleted (POST-only endpoint) and the Slack message was left in
  place deliberately, as the audit trail for this verification. CAMS fingerprint:
  `7aad7d43ae7c92a0`.
- No token values appear in this document or in any committed file — only lengths and, for Slack,
  the non-secret `xoxb-` format prefix. Environment inspection was read-only via `ps eww`.

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
