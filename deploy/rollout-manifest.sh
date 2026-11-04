#!/usr/bin/env bash
# Roll a merged change of the shared state list (jurisdictions.yaml) out on THIS host: gates, pull, checks, the copy
# api-v3 reads, and a printed value for every step (OPEN-483). It replaces the same hand steps every state needed on each
# host (pull, record the revision, validate, drift check, refresh api-v3's copy, read the values back).
#
#   bash deploy/rollout-manifest.sh --host mac|ec2 --ddp-sync-root PATH [--dry-run] [--recreate]
#                                   [--skip-ecs-check] [--state XX] [--python PATH]
#
#   --host           mac -> deploy/docker-compose.ddp.yml, ec2 -> deploy/docker-compose.rds.yml
#   --ddp-sync-root  ddp-sync's checkout: the combined drift check compares both repos. REQUIRED for a real run (a
#                    repo-only check is not the combined check); a dry run without it prints the check as UNCHECKED.
#   --dry-run        change NOTHING in the working tree, the copy or any container; print every step and value.
#                    (It still runs `git fetch`, which moves only origin/main, never the checkout; and it validates the
#                    INCOMING file, read from origin/main, so a bad list is caught before anyone pulls it.)
#   --recreate       the ONE-TIME switch of an api container that still has the old single-file mount (see below)
#   --skip-ecs-check proceed when the cloud scrape tasks cannot be listed here (that gate is then on you)
#   --state XX       also print that state's status and flags from the list at the end
#
# ORDER (so a bad list is never served): gates -> fetch -> pull -> validate and drift-check the pulled file ->
# only then refresh the copy api-v3 reads -> container checks. If a check fails after the pull, the PULLED CHECKOUT STAYS
# (a fast-forward is not undone) but api-v3's copy was NOT changed: it keeps serving the previous list. Fix the list on
# main, pull again, rerun.
#
# It stops at the FIRST failed gate or check. It never touches ddp-sync, the broker, the database container or any .env,
# and it never restarts anything: ddp-sync reads the list by modification time and is restarted only on a person's word when
# the drift check says its own lists changed. The only docker command it can run is
#   docker compose -p ddp-openstates -f <file> up -d --no-build --no-deps --force-recreate api      (only with --recreate)
#
# Exit codes: 0 done (or dry run complete); 1 a gate or check failed; 2 bad arguments; 3 the api container still has the
# old single-file mount and needs the one-time recreate (rerun with --recreate; read the compose file's own comment first).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${ROLLOUT_REPO:-$(cd "$HERE/.." && pwd)}"
HOST=""; DRY=0; RECREATE=0; SKIP_ECS=0; SYNC_ROOT=""; STATE=""
PY="${ROLLOUT_PYTHON:-}"

while [ $# -gt 0 ]; do
    case "$1" in
        --host) HOST="${2:-}"; shift 2 ;;
        --dry-run) DRY=1; shift ;;
        --recreate) RECREATE=1; shift ;;
        --skip-ecs-check) SKIP_ECS=1; shift ;;
        --ddp-sync-root) SYNC_ROOT="${2:-}"; shift 2 ;;
        --state) STATE="${2:-}"; shift 2 ;;
        --python) PY="${2:-}"; shift 2 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done
case "$HOST" in
    mac) COMPOSE="deploy/docker-compose.ddp.yml" ;;
    ec2) COMPOSE="deploy/docker-compose.rds.yml" ;;
    *) echo "STOP: --host mac|ec2 is required" >&2; exit 2 ;;
esac
if [ "$DRY" != 1 ] && [ -z "$SYNC_ROOT" ]; then
    echo "STOP: a real rollout needs --ddp-sync-root PATH (the combined drift check compares ddp-sync's lists with this one; a repo-only check is not the combined check). Nothing was changed." >&2
    exit 2
fi
if [ -z "$PY" ]; then
    if [ -x "$REPO/.venv/bin/python3" ]; then PY="$REPO/.venv/bin/python3"; else PY="python3"; fi
fi
CONTAINER="${ROLLOUT_CONTAINER:-ddp-openstates-api-1}"
HEALTH_TRIES="${ROLLOUT_HEALTH_TRIES:-20}"     # x ROLLOUT_WAIT seconds (default 3) = a 60 s bounded wait
WAIT="${ROLLOUT_WAIT:-3}"

say() { printf '\n==> %s\n' "$*"; }
val() { printf '    %s\n' "$*"; }
die() { printf '\nSTOP: %s\n' "$*" >&2; exit 1; }
hash_of() { if command -v md5sum >/dev/null 2>&1; then md5sum "$1" | cut -d' ' -f1; else md5 -q "$1"; fi; }
[ "$DRY" = 1 ] && echo "DRY RUN: nothing in the checkout, the copy or any container will be changed."

cd "$REPO"

say "0. Where this runs"
val "host: $HOST   repo: $REPO   compose file: $COMPOSE"
BRANCH="$(git branch --show-current)"
val "branch: $BRANCH"
[ "$BRANCH" = "main" ] || die "this checkout is on '$BRANCH', not main; a rollout only fast-forwards main"
[ -z "$(git status --porcelain --untracked-files=no)" ] || die "tracked files are modified in this checkout; a rollout never pulls over local edits"

say "1. Gates"
# (a) a REAL scrape, archive or people-refresh process. These all read this checkout (scripts, activate.sh, the list), and
# run-scrape-retrying.sh stays alive while it SLEEPS between attempts (up to 900 s) with no run-scrape.sh alive, so it is
# matched too. The listing is parsed by field: a real run is `<path>/<name>.sh ...`; or a SHELL whose first non-option
# argument is that script (`bash -x <path>/run-scrape.sh`, `bash -o pipefail run-scrape.sh`: the value of -o is skipped);
# or a known WRAPPER (env, nohup, caffeinate, time, sudo, nice, ionice, timeout, setsid, stdbuf, arch, doas) whose COMMAND (after its
# options and their values) is the job or a shell on it (`caffeinate -i run-scrape.sh`, `/usr/bin/time -p run-archive.sh`,
# `sudo -u git run-people-refresh.sh`, `nohup bash run-scrape.sh`) (OPEN-488).
# Anything else never matches: a shell that merely CONTAINS the text (`zsh -c "... run-scrape ..."`), a grep, an editor or an
# echo (also behind a wrapper), this script's own command line. A plain `ps | grep run-scrape` matched its
# own shell on 2026-11-03 and nearly caused a wrong call.
# ROLLOUT_PS_FILE (tests only): a file holding a fake `ps -axo pid=,command=` listing.
if [ -n "${ROLLOUT_PS_FILE:-}" ]; then PS_LIST="$(cat "$ROLLOUT_PS_FILE")"; else PS_LIST="$(ps -axo pid=,command=)"; fi
REAL_SCRAPES="$(printf '%s\n' "$PS_LIST" | awk '
    function base(p,   a, n) { n = split(p, a, "/"); return a[n] }
    function is_shell(b) { return b == "bash" || b == "sh" || b == "zsh" || b == "dash" || b == "ksh" }
    function is_job(b) { return b == "run-scrape.sh" || b == "run-scrape-retrying.sh" || b == "run-archive.sh" || b == "run-people-refresh.sh" }
    function is_wrapper(b) { return b == "env" || b == "nohup" || b == "caffeinate" || b == "time" || b == "sudo" || b == "nice" || b == "ionice" || b == "timeout" || b == "setsid" || b == "stdbuf" || b == "arch" || b == "doas" }
    # Options of a wrapper that take a VALUE as the next field (`sudo -u git`, `caffeinate -t 60`, `nice -n 5`): that value is
    # never the wrapped command. A wrapper not listed here and an option not listed take no value.
    function takes_value(w, o) {
        if (w == "sudo") return o ~ /^-[ughpCDRTU]$/
        if (w == "doas") return o ~ /^-[uC]$/
        if (w == "caffeinate") return o ~ /^-[tw]$/
        if (w == "nice") return o == "-n"
        if (w == "ionice") return o ~ /^-[cnpPu]$/
        if (w == "timeout") return o ~ /^-[sk]$/
        if (w == "env") return o ~ /^-[uCS]$/
        if (w == "time") return o ~ /^-[fo]$/
        if (w == "stdbuf") return o ~ /^-[ioe]$/
        if (w == "arch") return o == "-arch"
        return 0
    }
    # `bash [-x -e -o name ...] run-scrape.sh ...` runs the script; `bash -c "..."` merely carries text, and the script it
    # starts is a child process of its own that this listing shows separately.
    function shell_scan(k,   j) {
        for (j = k; j <= NF; j++) {
            if ($j ~ /^-[A-Za-z]*c[A-Za-z]*$/) return
            if ($j ~ /^[-+][A-Za-z]*[oO]$/ || $j == "--rcfile" || $j == "--init-file") { j++; continue }
            if ($j ~ /^[-+]/) continue
            if (is_job(base($j))) print $1 " " base($j)
            return
        }
    }
    # `<wrapper> [options and their values] [NAME=value] [duration] <command> ...`: find the COMMAND the wrapper runs, and only
    # that: `nohup echo run-scrape.sh` and `sudo vim run-scrape.sh` run echo and vim, `sudo -u git bash run-scrape.sh` runs bash.
    function wrapper_scan(w, k,   j, bj) {
        for (j = k; j <= NF; j++) {
            if ($j ~ /^-/) { if (takes_value(w, $j)) j++; continue }
            if (w == "env" && $j ~ /=/) continue
            if (w == "timeout" && $j ~ /^[0-9.]+[smhd]?$/) continue
            bj = base($j)
            if (is_job(bj)) print $1 " " bj
            else if (is_shell(bj)) shell_scan(j + 1)
            else if (is_wrapper(bj)) wrapper_scan(bj, j + 1)
            return
        }
    }
    {
        b = base($2)
        if (is_job(b)) { print $1 " " b; next }
        if (is_shell(b)) { shell_scan(3); next }
        if (is_wrapper(b)) wrapper_scan(b, 3)
    }')"
if [ -n "$REAL_SCRAPES" ]; then
    die "a real scrape, archive or people-refresh job is running ($(echo "$REAL_SCRAPES" | tr '\n' ';')); leave this checkout alone until it finishes"
fi
val "real run-scrape / run-scrape-retrying / run-archive / run-people-refresh processes: 0"
# (b) cloud scrape tasks
if [ "$SKIP_ECS" = 1 ]; then
    val "cloud scrape tasks: NOT CHECKED (--skip-ecs-check): the gate is on you"
elif command -v aws >/dev/null 2>&1; then
    TASKS="$(aws ecs list-tasks --cluster ddp-scrapers --region us-east-1 --query 'taskArns' --output text 2>&1)" \
        || die "cannot list the cloud scrape tasks here ($TASKS); check them another way and rerun with --skip-ecs-check"
    [ -z "$TASKS" ] || [ "$TASKS" = "None" ] || die "cloud scrape tasks are running: $TASKS"
    val "cloud scrape tasks: 0"
else
    die "the aws CLI is not available to list cloud scrape tasks; check them another way and rerun with --skip-ecs-check"
fi
# (c) not near the 02:00, 02:30 and 03:00 UTC jobs
NOW_UTC="${ROLLOUT_NOW_UTC:-$(date -u +%H:%M)}"
NOW_MIN=$((10#${NOW_UTC%:*} * 60 + 10#${NOW_UTC#*:}))
for t in 120 150 180; do
    d=$((NOW_MIN - t)); [ $d -lt 0 ] && d=$((-d))
    [ $d -gt 10 ] || die "it is $NOW_UTC UTC, within 10 minutes of the $((t/60)):$(printf %02d $((t%60))) job; try later"
done
val "time: $NOW_UTC UTC (not within 10 minutes of 02:00, 02:30 or 03:00)"

say "2. Revision before, and what would come in"
BEFORE="$(git rev-parse --short HEAD)"
val "revision now: $BEFORE ($(git log -1 --format=%s | cut -c1-70))"
git fetch -q origin main
if [ "$DRY" = 1 ]; then val "(a dry run still runs git fetch: it moves origin/main only, never the checkout)"; fi
AHEAD="$(git rev-list --count origin/main..HEAD)"
val "local commits not on origin/main: $AHEAD"
if [ "$AHEAD" != "0" ]; then
    die "this checkout has $AHEAD commit(s) that are not on origin/main; a rollout only deploys what is merged (nothing was changed)"
fi
INCOMING="$(git log --oneline HEAD..origin/main | wc -l | tr -d ' ')"
val "commits to pull: $INCOMING"
if [ "$INCOMING" != "0" ]; then
    git log --oneline HEAD..origin/main | sed 's/^/      /'
    git diff --stat HEAD origin/main | tail -8 | sed 's/^/      /'
fi

say "3. Pull (fast-forward only)"
CHECK_FILE="$REPO/jurisdictions.yaml"
if [ "$INCOMING" = "0" ]; then
    val "already up to date"
elif [ "$DRY" = 1 ]; then
    val "(dry run) would: git merge --ff-only origin/main"
    CHECK_FILE="$(mktemp "${TMPDIR:-/tmp}/rollout-incoming.XXXXXX")"
    trap 'rm -f "$CHECK_FILE"' EXIT
    git show origin/main:jurisdictions.yaml > "$CHECK_FILE"
    val "(dry run) the checks below run on the INCOMING file (origin/main:jurisdictions.yaml), not the current one"
else
    git merge --ff-only -q origin/main || die "not a fast-forward; nothing was changed"
    val "revision now: $(git rev-parse --short HEAD)"
    [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || die "after the pull this checkout is not at origin/main"
fi
AFTER="$(git rev-parse --short HEAD)"

say "4. Checks that only read (BEFORE api-v3's copy is touched)"
FAILURE_NOTE="the checkout is now at $AFTER (a fast-forward is not undone); api-v3's copy of the list was NOT changed and keeps serving the previous list"
[ "$DRY" = 1 ] && FAILURE_NOTE="nothing was changed (dry run)"
"$PY" validate_jurisdictions.py "$CHECK_FILE" | sed 's/^/    /' || die "jurisdictions.yaml does not validate; $FAILURE_NOTE"
if [ -n "$SYNC_ROOT" ]; then
    "$PY" check-jurisdiction-drift.py --manifest "$CHECK_FILE" --ddp-sync-root "$SYNC_ROOT" | sed 's/^/    /' \
        || die "the combined drift check failed (ddp-sync's lists and this list disagree); $FAILURE_NOTE"
else
    val "UNCHECKED: the combined drift check was NOT run (no --ddp-sync-root); this dry run says nothing about ddp-sync's lists"
fi

say "5. api-v3's copy of the list (the first change to anything api-v3 serves)"
if [ "$DRY" = 1 ]; then
    bash deploy/sync-manifest.sh --check || val "(dry run) the copy differs or is missing: a real run would refresh it"
else
    bash deploy/sync-manifest.sh | sed 's/^/    /'
    bash deploy/sync-manifest.sh --check | sed 's/^/    /'
fi

say "6. The api-v3 container"
# Every inspect and exec below targets the container's ID (read once here, and again after a recreate), never the name.
container_id() { docker inspect -f '{{.Id}}' "$CONTAINER" 2>/dev/null; }
CID="$(container_id)" && [ -n "$CID" ] || die "container $CONTAINER not found on this host"
val "container id: ${CID:0:12}"
mounts_of() { docker inspect -f '{{range .Mounts}}{{.Destination}} {{end}}' "$CID"; }
MOUNTS="$(mounts_of)"
val "mounts: $MOUNTS"
case " $MOUNTS " in
    *" /app/manifest "*) val "directory mount: yes (a pull needs no recreate)" ;;
    *)
        val "directory mount: NO (still the old single-file mount: it cannot see a pull)"
        if [ "$RECREATE" != 1 ]; then
            echo "ONE-TIME SWITCH NEEDED: rerun with --recreate (read the compose file's own HARD PRECONDITION comment first)." >&2
            exit 3
        fi
        if [ "$DRY" = 1 ]; then
            val "(dry run) would: docker compose -p ddp-openstates -f $(basename "$COMPOSE") up -d --no-build --no-deps --force-recreate api"
        else
            ( cd deploy && docker compose -p ddp-openstates -f "$(basename "$COMPOSE")" up -d --no-build --no-deps --force-recreate api ) | sed 's/^/    /'
            CID="$(container_id)" && [ -n "$CID" ] || die "container $CONTAINER not found after the recreate"
            val "container id after the recreate: ${CID:0:12}"
            MOUNTS="$(mounts_of)"
            val "mounts after the recreate: $MOUNTS"
        fi
        ;;
esac

say "7. Health and values read back"
HEALTH=""
for _ in $(seq 1 "$HEALTH_TRIES"); do
    HEALTH="$(docker inspect -f '{{.State.Health.Status}}' "$CID" 2>/dev/null || echo unknown)"
    [ "$HEALTH" = "healthy" ] && break
    sleep "$WAIT"
done
val "container health: $HEALTH"
[ "$HEALTH" = "healthy" ] || die "$CONTAINER is not healthy (status: $HEALTH) after $((HEALTH_TRIES * WAIT)) s; $FAILURE_NOTE (the container was left as it is)"
HOSTFILE="$REPO/jurisdictions.yaml"
val "revision: $BEFORE -> $AFTER"
val "md5 checkout file: $(hash_of "$HOSTFILE")"
if [ -f deploy/manifest/jurisdictions.yaml ]; then val "md5 api copy:      $(hash_of deploy/manifest/jurisdictions.yaml)"; else val "api copy: missing"; fi
case " $MOUNTS " in
    *" /app/manifest "*)
        CMD5="$(docker exec "$CID" sh -c 'md5sum /app/manifest/jurisdictions.yaml 2>/dev/null | cut -d" " -f1' 2>/dev/null || true)"
        val "md5 inside the container: ${CMD5:-EMPTY}"
        [ -n "$CMD5" ] || die "the container mounts /app/manifest but cannot read jurisdictions.yaml there (the copy is missing or empty); $FAILURE_NOTE"
        if [ "$DRY" != 1 ] && [ "$CMD5" != "$(hash_of "$HOSTFILE")" ]; then
            die "the container's copy does not match the checkout (container $CMD5); $FAILURE_NOTE"
        fi
        ;;
    *) val "md5 inside the container: not applicable (old single-file mount; dry run of the one-time switch)" ;;
esac
"$PY" - "$STATE" <<'PYEOF'
import collections, sys, yaml
d = yaml.safe_load(open("jurisdictions.yaml"))
by = collections.defaultdict(list)
for code, e in d.items():
    if isinstance(e, dict) and "status" in e:
        by[e["status"]].append(code)
print(f"    jurisdictions in the list: {sum(len(v) for v in by.values())}")
for status in sorted(by):
    print(f"      {status}: {' '.join(sorted(by[status]))}")
state = sys.argv[1].lower()
if state:
    e = d.get(state)
    if not isinstance(e, dict):
        print(f"    state {state}: not in the list")
    else:
        flags = " ".join(f"{k}={v}" for k, v in e["enrollment"].items())
        print(f"    state {state}: status={e['status']} tier={e['tier']} archive.enabled={e['archive']['enabled']} "
              f"archive.scheduled={e['archive']['scheduled']} {flags}")
PYEOF
say "Done. Not done by this script, on purpose: no ddp-sync restart, no broker or database change, no .env change."
echo "    (ddp-sync reads the list by modification time; restart it only on a person's word when the drift check says its own lists changed.)"
