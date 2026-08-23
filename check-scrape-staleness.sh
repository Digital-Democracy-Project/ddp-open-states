#!/usr/bin/env bash
# check-scrape-staleness.sh — scraper staleness watchdog (OPEN-40, PLAN-open-states §11.3)
#
# Detects jurisdictions that silently stop scraping. Every other failure path in
# this repo (run-scrape.sh's ERR trap / on_failure) fires only from INSIDE a run;
# nothing noticed "this job should have produced a fresh logs/last-run/<key>.ts
# by now and didn't" — which is exactly how MA ran wrong for six weeks in silence.
#
# Invoked every 5 minutes by the existing com.ddp.health-monitor LaunchDaemon via a
# one-line `bash <this script> || true` hook in ddp-agents/deployment/scripts/
# health-check-slack.sh — deliberately OUTSIDE ddp-sync and the scrape scripts, so
# the watchdog survives every failure mode it exists to catch, including "the
# scheduler daemon itself is dead" (observed live: ddp-sync down 2026-07-04→08,
# nothing alerted). Runs as root under that daemon; sentinel files it writes into
# logs/last-run/ will be root-owned (the directory is agentsmith-owned, so manual
# cleanup still works).
#
# Self-contained on purpose: sources nothing from this repo, so it cannot be broken
# by the things it monitors. The Slack/CAMS block below is a copy of run-scrape.sh's
# on_failure()/report_failure_to_cams() pattern — the fifth copy in this repo.
# OPEN-43 tracks extracting a shared helper; this script may stay a deliberate copy
# even then (monitoring shouldn't share code with the monitored).
#
# Alert lifecycle per key (sentinel de-dupe + escalation tiers, OPEN-130):
#   stale, no sentinel        -> alert (tier 1) Slack #automation-errors + CAMS,
#                                write <key>.stale-alerted recording tier=1
#   stale, same tier          -> silent (already alerted at this severity)
#   stale, crossed 2x/4x      -> RE-alert, escalated wording, bump tier in sentinel
#   stale, past 4x            -> silent again (4x is the top tier)
#   fresh + sentinel          -> remove sentinel, post recovery message
#   missing .ts entirely      -> maximally stale (alerts, never skips), pinned to
#                                the top tier: there is no growth left to report
#
# Why tiers (OPEN-130): the pre-tier version alerted exactly once, at the moment
# the condition looked LEAST serious ("az last run 229h, threshold 228h" reads as
# a rounding error), and then the sentinel correctly silenced it while the real
# staleness grew — az reached 14 days with nobody alerted again. All three
# staleness alerts ever sent were declined by CodeBot triage as "not a code bug",
# which was the designed response to a one-line signal that cannot be told apart
# from a scraper legitimately quiet out of session.
#
# So the alert body now carries its own evidence: absolute last-success date,
# count of MISSED SCHEDULED RUNS, and the multiple of threshold. The load-bearing
# fact is the missed-run count, because run-scrape.sh's finish_no_op() stamps
# <key>.ts even on a zero-bill run — an out-of-session jurisdiction still
# refreshes its marker, so a stale marker means the scheduled job is not
# completing, NOT that there was nothing to scrape.
#
# Escalation wording deliberately changes WORDS per tier, not just numbers:
# CAMS's failure fingerprint normalizes all digits to <n>
# (ddp-agents failure_watcher._normalize), so "now 2x" and "now 4x" would
# collapse into one de-duped signal if the tiers differed only numerically.
#
# STALE_* env vars below are test seams (see test-check-scrape-staleness.sh) —
# production (the health-monitor hook) sets none of them.

set -uo pipefail

REPO_DIR=/Users/agentsmith/Developer/repos/ddp-open-states
LOG_DIR="$REPO_DIR/logs"
LAST_RUN_DIR="${STALE_LAST_RUN_DIR:-$LOG_DIR/last-run}"
LOG_FILE="${STALE_LOG_FILE:-$LOG_DIR/staleness-check.log}"
DRY_RUN="${STALE_DRY_RUN:-0}"
NOW_EPOCH="${STALE_NOW_EPOCH:-$(date +%s)}"
MISSING_AGE_HOURS=999999   # "maximally stale" — a missing marker always exceeds any threshold

# Own log file, not scraper.log: this runs every 5 minutes under the monitor and
# quiet runs log nothing, but scraper.log's rotation/summary greps shouldn't have
# to filter watchdog chatter. Same log() shape as run-scrape.sh (local-time variant).
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

# --- Watched key -> deadline map, DERIVED from ddp-sync's schedule (OPEN-135) ----
#
# Still emits `key:threshold_hours` so everything below is unchanged, but the pairs
# are now computed from ddp-sync's own config/sync_schedule.yaml instead of being
# typed out here.
#
# WHY. The map this replaces carried its own warning: "This map is THE thing to
# touch when the ddp-sync schedule changes." That is a hand-maintained coupling
# between two repos, and it drifted exactly as you would expect. It also could not
# express the actual question. Arizona sat 14 days stale having produced one alert
# reading "229h vs a 228th threshold" — which triage reasonably dismissed as a
# rounding error, because 228 was a hand-picked number standing in for "a weekly
# job missed its run", not the thing itself.
#
# WHAT CHANGED. A threshold is now derived per key from that job's real schedule:
#
#     threshold = hours since that job's most recent scheduled run
#     ...unless we are still within the grace window, in which case nothing alerts
#
# Read it as a question about the marker rather than about elapsed time: is the
# marker older than the moment the last run was due to start? If it is, that run
# cannot have written it, so a scheduled run has been and gone without completing.
# If it is newer, the run completed. The grace window covers the hours a run
# legitimately takes — during it the marker is still a full cadence old and must
# not alert.
#
# So the alert condition is now "a run was scheduled and did not complete", at
# whatever cadence the schedule happens to say, rather than a hand-picked number of
# hours standing in for that.
#
# Consequences worth knowing:
#   - FL flipping between daily and weekly for its session needs no edit here.
#   - A new jurisdiction in sync_schedule.yaml is watched automatically.
#   - A jurisdiction removed from the schedule stops being watched, rather than
#     alerting forever.
#
# STILL AN ALLOWLIST. Derived from the schedule, never from globbing
# logs/last-run/ — that directory also holds one-time backfill markers
# (fl_session_2023..2025C, usa_session_118_*) which correctly never update and must
# never be watched.
#
# THE ONE THING NOT TO CHANGE. This watchdog runs OUTSIDE ddp-sync on purpose, so
# it survives the scheduler being dead — which happened unnoticed 2026-07-04 to
# 07-08. Reading ddp-sync's config file does not weaken that (a file is readable
# whether or not the process is alive), but it does introduce a way to fail, so an
# unreadable or unparseable schedule ALERTS rather than quietly watching nothing.
# Operator decision, 2026-08-23: read the real schedule, alarm if it cannot be
# read, do not keep a second copy here to drift again.
SCHEDULE_FILE="${STALE_SCHEDULE_FILE:-/Users/agentsmith/Developer/repos/ddp-sync/config/sync_schedule.yaml}"
GRACE_HOURS="${STALE_GRACE_HOURS:-24}"

derive_watchlist() {
    python3 - "$SCHEDULE_FILE" "$GRACE_HOURS" "$NOW_EPOCH" <<'PY'
import sys, yaml, datetime

path, grace_h, now_epoch = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
cfg = yaml.safe_load(open(path))
block = (cfg or {}).get("openstates_scrape") or {}
if not block:
    raise SystemExit("no openstates_scrape block in schedule")

DAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6}
now = datetime.datetime.fromtimestamp(now_epoch, datetime.timezone.utc)


def hhmm(s, default="02:00"):
    try:
        h, m = str(s or default).split(":")[:2]
        return int(h), int(m)
    except (ValueError, AttributeError):
        return 2, 0


# Large but finite. Used as "not due yet", and deliberately just under
# MISSING_AGE_HOURS (999999) so a job that has NEVER produced a marker still
# alerts even inside its grace window -- there is no run in progress to wait for.
NOT_DUE_YET = 999998


def threshold_for(sync_day, sync_time):
    """Hours of marker-age that mean "the most recent scheduled run did not complete".

    The threshold is simply *hours since that run was scheduled*. If the marker is
    older than that, it predates the run, so the run did not write it.

        marker younger than the scheduled time  -> it completed        -> quiet
        marker older   than the scheduled time  -> it did not          -> alert

    And while we are still inside the grace window after a scheduled time, nothing
    alerts at all: the job is probably still running, and its marker is legitimately
    a full cadence old until the moment it finishes.

    Worth spelling out why the obvious-looking alternative is wrong. Anchoring on the
    run BEFORE the most recent one produces a threshold that grows at exactly the same
    rate as the marker ages, so the comparison never trips: by the following Saturday a
    weekly job that missed its Sunday has an age of 312h against a threshold of 336h and
    reports healthy. Anchoring on the most recent scheduled time is what makes this
    "a scheduled run did not complete" rather than another elapsed-hours proxy.
    """
    h, m = hhmm(sync_time)
    at = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if sync_day is None:
        prev = at if at <= now else at - datetime.timedelta(days=1)
    else:
        target = DAYS[str(sync_day).strip().lower()]
        back = (now.weekday() - target) % 7
        prev = at - datetime.timedelta(days=back)
        if prev > now:
            prev -= datetime.timedelta(days=7)
    since = int((now - prev).total_seconds() // 3600)
    return since if since > grace_h else NOT_DUE_YET


def key_for(state, session_arg):
    raw = f"{state} {session_arg}" if session_arg else state
    return raw.replace(" ", "_").replace("=", "_")


out = []

# primary: one entry per jurisdiction, times one per configured session
for state, jcfg in (block.get("primary") or {}).items():
    if not isinstance(jcfg, dict) or not jcfg.get("enabled", False):
        continue
    day = jcfg.get("sync_day")
    when = jcfg.get("sync_time_utc")
    sessions = jcfg.get("sessions") or [None]
    for s in sessions:
        arg = f"session={s}" if s else None
        out.append((key_for(state, arg), threshold_for(day, when)))

# secondary: bare jurisdiction keys. ddp-sync passes session_arg=None for every
# secondary (OPEN-24: VA and UT each had two simultaneously-active sessions), so
# run-scrape.sh derives SCRAPE_KEY=<state> and writes <state>.ts. Deriving a
# session-qualified key here would watch a file that is never written.
sec = block.get("secondary") or {}
if sec.get("enabled", False):
    overdue = threshold_for(sec.get("sync_day"), sec.get("sync_time_utc"))
    for state in sec.get("jurisdictions") or []:
        out.append((key_for(state, None), overdue))

if not out:
    raise SystemExit("schedule parsed but produced no watched keys")
for k, t in out:
    print(f"{k}:{t}")
PY
}

# The watchlist is resolved further down, after the alerting helpers are defined --
# a derivation failure needs to alert, and post_slack/post_cams do not exist yet
# at this point in the file.

# --- Alerting (copy of run-scrape.sh's pattern — see OPEN-43 header note) --------

SLACK_TOKEN=""
CAMS_TOKEN=""
CAMS_URL="${CAMS_URL:-http://localhost:8000}"
if [ "$DRY_RUN" != "1" ]; then
    SLACK_TOKEN=$(grep -E '^SLACK_BOT_TOKEN=' /Users/agentsmith/Developer/repos/ddp-agents/.env \
        2>/dev/null | head -1 | cut -d'=' -f2- | tr -d '"'"'" | awk '{print $1}')
    CAMS_TOKEN=$(grep -E '^CAMS_API_TOKEN=' /Users/agentsmith/Developer/repos/ddp-agents/.env \
        2>/dev/null | head -1 | cut -d'=' -f2- | tr -d '"'"'" | awk '{print $1}')
fi

post_slack() {
    # $1 = message text. Keys/ages are hardcoded/derived alphanumerics, so inline
    # JSON is injection-safe here (same reasoning as run-scrape.sh's on_failure).
    if [ "$DRY_RUN" = "1" ]; then
        echo "DRY_RUN slack: $1"
        return 0
    fi
    [ -n "$SLACK_TOKEN" ] && curl -sf --max-time 10 \
        -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $SLACK_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"channel\": \"#automation-errors\", \"text\": \"$1\"}" \
        >/dev/null || true
}

post_cams() {
    # $1 = message, $2 = key, $3 = age display, $4 = threshold hours,
    # $5 = evidence block (multi-line), $6 = tier, $7 = missed runs, $8 = last success.
    # Best-effort POST to CAMS /api/v1/failures so a real staleness episode reaches
    # Agent Smith triage, not just Slack. curl -sf + || true throughout: an alerting
    # outage must never break the health monitor this script runs under.
    #
    # $5 goes in `stacktrace` (an accepted FailureReport field, ddp-agents
    # cams/api/routes.py) because triage renders it as "Stacktrace / details" and
    # previously received "(none provided)" — the whole reason OPEN-130 exists.
    # No ddp-agents change is needed for this: the fields were always accepted.
    if [ "$DRY_RUN" = "1" ]; then
        echo "DRY_RUN cams: ScrapeStalenessDetected key=$2 age=$3 threshold=${4}h tier=$6 missed_runs=$7 last_success=$8"
        echo "DRY_RUN cams details: $5"
        return 0
    fi
    [ -n "$CAMS_TOKEN" ] || return 0
    python3 -c '
import json, sys
print(json.dumps({
    "v": 1,
    "service": "ddp-open-states",
    "error_type": "ScrapeStalenessDetected",
    "message": sys.argv[1],
    "stacktrace": sys.argv[5],
    "severity_hint": "high" if sys.argv[6] != "1" else "warning",
    "metadata": {
        "key": sys.argv[2], "age": sys.argv[3], "threshold_hours": sys.argv[4],
        "escalation_tier": sys.argv[6], "scheduled_runs_missed": sys.argv[7],
        "last_success": sys.argv[8],
    },
}))
' "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" 2>/dev/null | \
        curl -sf --max-time 10 -X POST "$CAMS_URL/api/v1/failures" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $CAMS_TOKEN" \
            -d @- >/dev/null || true
}

# --- Evidence derivation (OPEN-130) ----------------------------------------------
#
# The watchlist's threshold IS the cadence signal — see the map above: 48h means a
# daily job (2x cadence), 228h means a weekly job (~9.5d on a 7d cadence). Kept as
# an explicit case, not arithmetic, so a new threshold has to be thought about
# rather than silently producing a fabricated missed-run count. Unknown threshold
# falls back to cadence == threshold, which UNDER-counts misses (>= 1 when past the
# threshold) rather than inventing them.
cadence_hours_for() {
    case "$1" in
        48)  echo 24  ;;   # daily jobs
        228) echo 168 ;;   # weekly jobs
        *)   echo "$1" ;;  # unknown threshold: conservative, never over-counts
    esac
}

cadence_label_for() {
    case "$1" in
        24)  echo "daily"  ;;
        168) echo "weekly" ;;
        *)   echo "every ${1}h" ;;
    esac
}

# 72 -> "3 days"; 30 -> "30h". Days are what makes "this is bad" legible; hours
# stay in the message too because the threshold is expressed in hours.
human_hours() {
    if [ "$1" -ge 48 ]; then echo "$(( $1 / 24 )) days"; else echo "${1}h"; fi
}

# age threshold -> "1.4" (one decimal, integer math only — no bc on this box path)
multiple_display() {
    local tenths=$(( $1 * 10 / $2 ))
    echo "$(( tenths / 10 )).$(( tenths % 10 ))"
}

# age threshold -> 1 | 2 | 4 (escalation tier; 4 is the top tier)
tier_for() {
    if   [ "$1" -ge $(( $2 * 4 )) ]; then echo 4
    elif [ "$1" -ge $(( $2 * 2 )) ]; then echo 2
    else echo 1
    fi
}

# sentinel_field <file> <name> -> value, or "" when absent. grep/cut rather than
# sourcing: the sentinel is a root-written file in a user-writable directory, so it
# is data, never code. Absent field also covers pre-OPEN-130 sentinels, which hold
# a bare timestamp — those read as tier "" and are treated as tier 1 below, so an
# in-flight staleness episode upgrades cleanly instead of re-alerting.
sentinel_field() {
    [ -f "$1" ] || return 0
    grep -E "^$2=" "$1" 2>/dev/null | tail -1 | cut -d= -f2-
}

# write_sentinel <file> <tier> <first_utc> <first_epoch> <first_age_hours>
write_sentinel() {
    printf 'tier=%s\nfirst_alerted_utc=%s\nfirst_alerted_epoch=%s\nfirst_alerted_age_hours=%s\nlast_alerted_utc=%s\n' \
        "$2" "$3" "$4" "$5" "$(date -u +%Y-%m-%dT%H:%M:%S)" > "$1"
}

# --- Resolve the watchlist (OPEN-135) --------------------------------------------
#
# Here rather than beside derive_watchlist() because a derivation failure has to
# alert, and post_slack/post_cams are only defined above this line.
if [ -n "${STALE_WATCHLIST:-}" ]; then
    WATCHLIST="$STALE_WATCHLIST"
else
    DERIVE_ERR=$(mktemp)
    if ! WATCHLIST=$(derive_watchlist 2>"$DERIVE_ERR"); then
        reason=$(tr '\n' ' ' < "$DERIVE_ERR" | tail -c 300)
        rm -f "$DERIVE_ERR"
        # Loudly, and non-zero. The alternative — fall back to an empty watchlist
        # and report every jurisdiction healthy — is the one outcome a watchdog
        # must never produce, and it is what this script did for its whole life
        # if the hardcoded map went stale.
        log "ERROR: cannot derive the watchlist from $SCHEDULE_FILE — watching NOTHING this run: $reason"
        post_slack "🚨 *Staleness watchdog cannot read the scrape schedule* — \`$SCHEDULE_FILE\` is missing or unparseable, so no jurisdiction is being watched for staleness right now. This is the watchdog itself being blind, not a quiet night. Error: \`${reason}\`"
        post_cams "staleness watchdog could not read $SCHEDULE_FILE: $reason" \
            "schedule" "unreadable" "0"
        exit 1
    fi
    rm -f "$DERIVE_ERR"
    log "watching $(echo "$WATCHLIST" | grep -c ':') keys derived from $SCHEDULE_FILE (grace ${GRACE_HOURS}h)"
fi

# --- Main check ------------------------------------------------------------------

for entry in $WATCHLIST; do
    key="${entry%%:*}"
    threshold_hours="${entry##*:}"
    ts_file="$LAST_RUN_DIR/$key.ts"
    sentinel="$LAST_RUN_DIR/$key.stale-alerted"
    cadence_hours=$(cadence_hours_for "$threshold_hours")
    cadence_label=$(cadence_label_for "$cadence_hours")

    if [ -f "$ts_file" ]; then
        mtime=$(stat -f %m "$ts_file" 2>/dev/null || echo 0)   # BSD stat (this Mac), not GNU
        age_hours=$(( (NOW_EPOCH - mtime) / 3600 ))
        age_display="${age_hours}h"
        last_success=$(date -r "$mtime" '+%Y-%m-%d %H:%M %Z' 2>/dev/null || echo "unknown")
        # Scheduled runs that should have completed since the last success and
        # didn't. Floor division: 336h stale on a 168h weekly cadence = 2 missed.
        missed_runs=$(( age_hours / cadence_hours ))
        mult_display=$(multiple_display "$age_hours" "$threshold_hours")
        severity_phrase="${mult_display}× threshold"
        # Days for legibility, hours because the threshold is stated in hours.
        # Under 48h the two are the same number, so don't say it twice.
        if [ "$age_hours" -ge 48 ]; then
            headline="no successful scrape in $(human_hours "$age_hours") — ${age_display} (threshold ${threshold_hours}h), ${severity_phrase}"
        else
            headline="no successful scrape in ${age_display} (threshold ${threshold_hours}h), ${severity_phrase}"
        fi
        missed_phrase="${missed_runs} scheduled ${cadence_label} run(s) missed"
        missed_sentence="A marker this old means ${missed_runs} scheduled ${cadence_label} run(s) did not complete at all."
        last_success_detail="${last_success} (${age_display} ago)"
        marker_missing=0
    else
        # Missing marker = the job has NEVER succeeded (or someone removed the
        # marker) — maximally stale. Alerts, never skips (AC #3). Recorded at the
        # top tier: "never" cannot grow, so escalation could only add noise.
        age_hours=$MISSING_AGE_HOURS
        age_display="never (no ${key}.ts marker)"
        last_success="none on record"
        missed_runs="all"
        severity_phrase="no successful run on record at all"
        headline="no successful scrape ever recorded — ${age_display}, threshold ${threshold_hours}h"
        missed_phrase="No scheduled ${cadence_label} run has ever completed for this key"
        missed_sentence="There is no marker at all, so no scheduled ${cadence_label} run has ever completed for this key (or the marker was deleted)."
        last_success_detail="none on record — logs/last-run/${key}.ts does not exist"
        marker_missing=1
    fi

    if [ "$age_hours" -gt "$threshold_hours" ]; then
        prev_tier=$(sentinel_field "$sentinel" tier)
        # Pre-OPEN-130 sentinel (bare timestamp) or a hand-made one: treat as
        # "tier 1 already sent" so an in-flight episode escalates, not re-alerts.
        [ -f "$sentinel" ] && [ -z "$prev_tier" ] && prev_tier=1
        [ -z "$prev_tier" ] && prev_tier=0
        # A non-numeric tier= (typo in the RUNBOOK's hand-silence recipe, truncated
        # write) would make the -gt below an integer-expression error, which under
        # `set -uo pipefail` (no -e) evaluates false and SILENTLY suppresses the
        # alert — the exact failure this ticket exists to remove. Fall back to 0:
        # this run alerts and rewrites the sentinel cleanly, so it self-heals noisy
        # rather than silent.
        case "$prev_tier" in
            ''|*[!0-9]*)
                log "WARNING: sentinel $sentinel has non-numeric tier '${prev_tier}' — treating as un-alerted and rewriting"
                prev_tier=0 ;;
        esac
        cur_tier=$(tier_for "$age_hours" "$threshold_hours")
        [ "$marker_missing" = "1" ] && cur_tier=4   # missing marker: top tier, fires once

        if [ "$cur_tier" -gt "$prev_tier" ]; then
            first_utc=$(sentinel_field "$sentinel" first_alerted_utc)
            first_epoch=$(sentinel_field "$sentinel" first_alerted_epoch)
            first_age=$(sentinel_field "$sentinel" first_alerted_age_hours)
            if [ "$prev_tier" = "0" ]; then
                first_utc=$(date -u +%Y-%m-%dT%H:%M:%S)
                first_epoch="$NOW_EPOCH"
                first_age="$age_hours"
            fi

            if [ -n "$first_utc" ] && [ -n "$first_age" ]; then
                first_alert_note="first alerted ${first_utc} at ${first_age}h"
            else
                first_alert_note="first-alert details unrecorded (sentinel predates escalation tracking)"
            fi

            # Evidence block: what triage renders as "Stacktrace / details" and
            # previously got "(none provided)". The finish_no_op paragraph is the
            # point — it is the fact that separates "quiet, out of session" from
            # "this job is dead", and it is the judgement CodeBot declined three
            # times for want of exactly this.
            details="Staleness watchdog evidence (check-scrape-staleness.sh, OPEN-40):
  jurisdiction key:       ${key}
  last successful scrape: ${last_success_detail}
  staleness threshold:    ${threshold_hours}h (${severity_phrase})
  scheduled cadence:      ${cadence_label} (every ${cadence_hours}h)
  scheduled runs missed:  ${missed_runs}
  marker not refreshed:   logs/last-run/${key}.ts
  escalation tier:        ${cur_tier} (previous tier ${prev_tier}; ${first_alert_note})

This is a watchdog observation, not a caught exception, so there is no stacktrace:
no scrape process reported an error — the scheduled job simply did not complete.

A jurisdiction being out of session does NOT explain this. run-scrape.sh's
finish_no_op() stamps logs/last-run/${key}.ts even when a run scrapes zero bills,
so a legitimately-quiet jurisdiction still refreshes its marker every cycle.
${missed_sentence} Start at logs/scraper.log for ${key} and the ddp-sync schedule."

            # Wording branches on FIRST ALERT vs ESCALATION, not on tier number: a
            # key that jumps straight past 2x (watchdog or scheduler was itself
            # down) still deserves first-alert wording, while recording the tier it
            # actually reached so it doesn't immediately "escalate" to itself.
            if [ "$prev_tier" = "0" ]; then
                log "STALE: $key last-run age ${age_display} exceeds ${threshold_hours}h threshold (${missed_phrase}) — alerting (tier ${cur_tier})"
                msg="🕰️ *OpenStates scrape stale: ${key}* — ${headline}. Last success: ${last_success}. ${missed_phrase}. An out-of-session jurisdiction still refreshes its marker (run-scrape.sh finish_no_op), so this means the scheduled job is not completing. See ~/Developer/repos/ddp-open-states/RUNBOOK.md (staleness watchdog) and logs/scraper.log."
                cams_msg="scrape staleness: $key last run ${age_display}, threshold ${threshold_hours}h, ${missed_phrase}, last success ${last_success}"
            else
                # Distinct WORDS per tier, not just distinct numbers — see the
                # fingerprint note in the header comment.
                if [ "$cur_tier" = "4" ]; then
                    tier_word="SEVERELY stale"
                    tier_note="four times past its threshold"
                else
                    tier_word="STILL stale and getting worse"
                    tier_note="twice past its threshold"
                fi
                growth=""
                [ -n "$first_age" ] && [ "$first_age" != "$age_hours" ] \
                    && growth=" Was ${first_age}h when first alerted on ${first_utc}; it has grown since and nothing has recovered it."
                log "ESCALATING: $key age ${age_display} crossed tier ${cur_tier} (was tier ${prev_tier}) — re-alerting"
                msg="🚨 *OpenStates scrape ${tier_word}: ${key}* — ${tier_note}: ${headline}. Last success: ${last_success}. ${missed_phrase}.${growth} This is the same unresolved episode escalating, not a new outage. See ~/Developer/repos/ddp-open-states/RUNBOOK.md (staleness watchdog) and logs/scraper.log."
                cams_msg="scrape staleness ${tier_word}: $key has now gone ${age_display} with no successful run (${tier_note}, threshold ${threshold_hours}h), ${missed_phrase}, last success ${last_success}"
            fi

            post_slack "$msg"
            post_cams "$cams_msg" "$key" "$age_display" "$threshold_hours" \
                "$details" "$cur_tier" "$missed_runs" "$last_success"

            # Sentinel = "already alerted this episode, at this tier". If the write
            # fails we'd re-alert every 5 minutes, so log that loudly. Rewritten
            # (not appended) on escalation, preserving the first-alert fields so the
            # growth clause survives; root-owned rewrites by root are fine, and a
            # failed rewrite degrades to the old behaviour (noisy, not silent).
            write_sentinel "$sentinel" "$cur_tier" "$first_utc" "$first_epoch" "$first_age" \
                || log "ERROR: could not write sentinel $sentinel — $key will re-alert every run"
        fi
    else
        if [ -f "$sentinel" ]; then
            log "RECOVERED: $key fresh again (age ${age_display}, threshold ${threshold_hours}h) — clearing sentinel"
            rm -f "$sentinel" \
                || log "ERROR: could not remove sentinel $sentinel — recovery will re-post every run"
            post_slack "✅ *OpenStates scrape recovered: ${key}* — fresh last-run marker (age ${age_display}, threshold ${threshold_hours}h). Escalation state cleared."
        fi
    fi
done

exit 0
