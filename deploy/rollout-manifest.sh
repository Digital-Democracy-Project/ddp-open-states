#!/usr/bin/env bash
# Roll a merged change of the shared state list (jurisdictions.yaml) out on THIS host: gates, pull, copy for api-v3,
# checks, and a printed value for every step (OPEN-483). It replaces the same five hand steps that every state needed
# on each host (pull, record the revision, refresh api-v3's copy, run the drift check, read the values back).
#
#   bash deploy/rollout-manifest.sh --host mac|ec2 [--dry-run] [--ddp-sync-root PATH] [--recreate]
#                                   [--skip-ecs-check] [--python PATH]
#
#   --host        mac -> deploy/docker-compose.ddp.yml, ec2 -> deploy/docker-compose.rds.yml
#   --dry-run     change NOTHING: print every step and every value, and what it would do
#   --ddp-sync-root  ddp-sync's checkout (the combined drift check compares both); without it the drift check
#                 runs on this repo alone and says so
#   --recreate    the ONE-TIME switch of an api container that still has the old single-file mount (see below)
#   --skip-ecs-check  proceed when the cloud scrape tasks cannot be listed here (the gate is then on you)
#
# It stops at the FIRST failed gate or check. It never touches ddp-sync, the broker, the database container or any .env,
# and it never restarts anything: ddp-sync reads the list by modification time and is restarted only on a person's
# word when the drift check says its own lists changed. The only docker command it can run is
#   docker compose -p ddp-openstates -f <file> up -d --no-deps --force-recreate api      (only with --recreate)
#
# Exit codes: 0 done (or dry run complete); 1 a gate or check failed; 3 the api container still has the old
# single-file mount and needs the one-time recreate (rerun with --recreate; read the compose file's own comment first).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${ROLLOUT_REPO:-$(cd "$HERE/.." && pwd)}"
HOST=""; DRY=0; RECREATE=0; SKIP_ECS=0; SYNC_ROOT=""
PY="${ROLLOUT_PYTHON:-}"

while [ $# -gt 0 ]; do
    case "$1" in
        --host) HOST="${2:-}"; shift 2 ;;
        --dry-run) DRY=1; shift ;;
        --recreate) RECREATE=1; shift ;;
        --skip-ecs-check) SKIP_ECS=1; shift ;;
        --ddp-sync-root) SYNC_ROOT="${2:-}"; shift 2 ;;
        --python) PY="${2:-}"; shift 2 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done
case "$HOST" in
    mac) COMPOSE="deploy/docker-compose.ddp.yml" ;;
    ec2) COMPOSE="deploy/docker-compose.rds.yml" ;;
    *) echo "STOP: --host mac|ec2 is required" >&2; exit 2 ;;
esac
if [ -z "$PY" ]; then
    if [ -x "$REPO/.venv/bin/python3" ]; then PY="$REPO/.venv/bin/python3"; else PY="python3"; fi
fi
CONTAINER="${ROLLOUT_CONTAINER:-ddp-openstates-api-1}"

say() { printf '\n==> %s\n' "$*"; }
val() { printf '    %s\n' "$*"; }
die() { printf '\nSTOP: %s\n' "$*" >&2; exit 1; }
hash_of() { if command -v md5sum >/dev/null 2>&1; then md5sum "$1" | cut -d' ' -f1; else md5 -q "$1"; fi; }
[ "$DRY" = 1 ] && echo "DRY RUN: nothing will be changed."

cd "$REPO"

say "0. Where this runs"
val "host: $HOST   repo: $REPO   compose file: $COMPOSE"
BRANCH="$(git branch --show-current)"
val "branch: $BRANCH"
[ "$BRANCH" = "main" ] || die "this checkout is on '$BRANCH', not main; a rollout only fast-forwards main"
[ -z "$(git status --porcelain --untracked-files=no)" ] || die "tracked files are modified in this checkout; a rollout never pulls over local edits"

say "1. Gates"
# (a) a REAL scrape process. The listing is parsed by field: a real run is `<path>/run-scrape.sh ...`, or a shell (optionally
# behind `env`) whose first non-option argument is that script (`bash -x <path>/run-scrape.sh`). A shell that merely CONTAINS the text
# (`zsh -c "... run-scrape ..."`, a grep, this script's own command line) never matches: a plain `ps | grep run-scrape`
# matched its own shell on 2026-11-03 and nearly caused a wrong call.
if [ -n "${ROLLOUT_PS_CMD:-}" ]; then PS_LIST="$(eval "$ROLLOUT_PS_CMD")"; else PS_LIST="$(ps -axo pid=,command=)"; fi
REAL_SCRAPES="$(printf '%s\n' "$PS_LIST" | awk '
    function base(p,   a, n) { n = split(p, a, "/"); return a[n] }
    function is_shell(b) { return b == "bash" || b == "sh" || b == "zsh" || b == "dash" || b == "ksh" }
    {
        i = 2
        # `env [-opts] [NAME=value ...] cmd ...` runs cmd: look at cmd instead.
        if (base($i) == "env") { i++; while (i <= NF && ($i ~ /^-/ || $i ~ /=/)) i++ }
        if (base($i) == "run-scrape.sh") { print $1; next }
        if (is_shell(base($i))) {
            # `bash [-x -e ...] run-scrape.sh ...` runs the script; `bash -c "..."` merely carries text, and the
            # script it starts is a child process of its own that this listing shows separately.
            for (j = i + 1; j <= NF; j++) {
                if ($j ~ /^-[A-Za-z]*c[A-Za-z]*$/) break
                if ($j ~ /^-/) continue
                if (base($j) == "run-scrape.sh") print $1
                break
            }
        }
    }')"
if [ -n "$REAL_SCRAPES" ]; then die "a real run-scrape.sh process is running (pid $(echo $REAL_SCRAPES | tr '\n' ' ')); leave this checkout alone until it finishes"; fi
val "real run-scrape.sh processes: 0"
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
AHEAD="$(git rev-list --count origin/main..HEAD)"
val "local commits not on origin/main: $AHEAD"
[ "$AHEAD" = "0" ] || die "this checkout has $AHEAD commit(s) that are not on origin/main; a rollout only deploys what is merged (nothing was changed)"
INCOMING="$(git log --oneline HEAD..origin/main | wc -l | tr -d ' ')"
val "commits to pull: $INCOMING"
if [ "$INCOMING" != "0" ]; then
    git log --oneline HEAD..origin/main | sed 's/^/      /'
    git diff --stat HEAD origin/main | tail -8 | sed 's/^/      /'
fi

say "3. Pull (fast-forward only)"
if [ "$INCOMING" = "0" ]; then
    val "already up to date"
elif [ "$DRY" = 1 ]; then
    val "(dry run) would: git merge --ff-only origin/main"
else
    git merge --ff-only -q origin/main || die "not a fast-forward; nothing was changed"
    val "revision now: $(git rev-parse --short HEAD)"
fi
[ "$DRY" = 1 ] || [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || die "after the pull this checkout is not at origin/main"

say "4. api-v3's copy of the list"
if [ "$DRY" = 1 ]; then
    bash deploy/sync-manifest.sh --check || val "(dry run) the copy differs or is missing: a real run would refresh it"
else
    bash deploy/sync-manifest.sh | sed 's/^/    /'
    bash deploy/sync-manifest.sh --check | sed 's/^/    /'
fi

say "5. Checks that read only"
"$PY" validate_jurisdictions.py | sed 's/^/    /' || die "jurisdictions.yaml does not validate"
if [ -n "$SYNC_ROOT" ]; then
    "$PY" check-jurisdiction-drift.py --ddp-sync-root "$SYNC_ROOT" | sed 's/^/    /' || die "the combined drift check failed (ddp-sync's lists and this list disagree); not changing anything further"
else
    "$PY" check-jurisdiction-drift.py | sed 's/^/    /' || die "the drift check failed (run without --ddp-sync-root: only this repo was compared)"
    val "NOTE: ddp-sync was not compared (no --ddp-sync-root)"
fi

say "6. The api-v3 container"
if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then
    die "container $CONTAINER not found on this host"
fi
MOUNTS="$(docker inspect -f '{{range .Mounts}}{{.Destination}} {{end}}' "$CONTAINER")"
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
            val "(dry run) would: docker compose -p ddp-openstates -f $COMPOSE up -d --no-deps --force-recreate api"
        else
            ( cd deploy && docker compose -p ddp-openstates -f "$(basename "$COMPOSE")" up -d --no-deps --force-recreate api ) | sed 's/^/    /'
            sleep "${ROLLOUT_WAIT:-20}"
        fi
        ;;
esac

say "7. Values read back"
val "revision: $BEFORE -> $(git rev-parse --short HEAD)"
HOSTFILE="$REPO/jurisdictions.yaml"
val "md5 checkout file: $(hash_of "$HOSTFILE")"
[ -f deploy/manifest/jurisdictions.yaml ] && val "md5 api copy:      $(hash_of deploy/manifest/jurisdictions.yaml)" || val "api copy: missing"
val "container health: $(docker inspect -f '{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null || echo unknown)"
CMD5="$(docker exec "$CONTAINER" sh -c 'md5sum /app/manifest/jurisdictions.yaml 2>/dev/null | cut -d" " -f1' 2>/dev/null || true)"
val "md5 inside the container: ${CMD5:-not readable (old mount, or not recreated yet)}"
if [ "$DRY" != 1 ] && [ -n "$CMD5" ] && [ "$CMD5" != "$(hash_of "$HOSTFILE")" ]; then
    die "the container's copy does not match the checkout (container $CMD5)"
fi
"$PY" - <<'PYEOF'
import collections, yaml
d = yaml.safe_load(open("jurisdictions.yaml"))
by = collections.defaultdict(list)
for code, e in d.items():
    if isinstance(e, dict) and "status" in e:
        by[e["status"]].append(code)
print(f"    jurisdictions in the list: {sum(len(v) for v in by.values())}")
for status in sorted(by):
    print(f"      {status}: {' '.join(sorted(by[status]))}")
PYEOF
say "Done. Not done by this script, on purpose: no ddp-sync restart, no broker or database change, no .env change."
echo "    (ddp-sync reads the list by modification time; restart it only on a person's word when the drift check says its own lists changed.)"
