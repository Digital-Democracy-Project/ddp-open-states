#!/usr/bin/env bash
# Build, verify, push and register a new ddp-scrapers image -- the one command a human operator runs
# to deploy scraper changes to Fargate. Follows RUNBOOK.md -> "Deploying a Fargate image change".
# Run on the Mac (never the EC2 host), as yourself: it loads the AWS IAM credentials and the GitHub
# token from the dev checkout's .env, which an agent session can't be expected to read.
#
#   bash deploy-scrapers-image.sh              # verifies, pushes, then registers the new revision
#   CONFIRM=1 bash deploy-scrapers-image.sh    # same, but asks before the one step that goes live
#   TASK_RDS_SECRET_ARN=<arn> TASK_RDS_HOST=<host> TASK_RDS_PORT=5432 TASK_RDS_DBNAME=<db> \
#     bash deploy-scrapers-image.sh            # OPEN-633/639: also gives the ddp-scrapers-db definition (load and
#                                              # archive only) the RDS secret, once; later revisions copy it forward
#
#   DB_DROP_PLAIN_ENV=VA_API_KEY,CONGRESS_GOV_API_KEY \
#     bash deploy-scrapers-image.sh            # OPEN-880: removes those plain entries from ddp-scrapers-db only
#   COLLECTION_PLAIN_TO_SECRET=VA_API_KEY,CONGRESS_GOV_API_KEY TASK_VA_API_KEY_SECRET_ARN=<arn> \
#     TASK_CONGRESS_GOV_API_KEY_SECRET_ARN=<arn> bash deploy-scrapers-image.sh
#                                              # OPEN-880: on ddp-scrapers, those names become secrets (one secret ARN, or ARN:json-key::, each)
#                                              # and the plain entries are dropped; later revisions copy them forward
#
# Stops at the first failed check. Nothing goes live until the final register step.
#
# The image is built and checked on the Mac's TEST Docker VM (Colima profile `test`, on /Volumes/DDP-HOT), never on the
# main VM that runs CAMS's Postgres and Redis (OPEN-860, AGENTS-250): a --no-cache build of both forks filled the main
# VM's disk to 99% twice. If the test VM is not available the script stops before doing anything; it never falls back.
# DDP_COLIMA_TEST_SH overrides the path of ddp-agents' colima-test.sh (the script's own tests use it).
set -euo pipefail

REGION=us-east-1
REPO=350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers
CLUSTER=ddp-scrapers
WORK=/tmp/ddp-open-states-deploy
DEV_ENV="$HOME/Developer/repos/ddp-open-states-dev/.env"
say() { printf '\n==> %s\n' "$*"; }
die() { printf '\nSTOP: %s\n' "$*" >&2; exit 1; }

say "0a. Which Docker: the test VM on DDP-HOT, never the main VM (OPEN-860)"
COLIMA_TEST_SH="${DDP_COLIMA_TEST_SH:-$HOME/Developer/repos/ddp-agents/deployment/scripts/colima-test.sh}"
[ -r "$COLIMA_TEST_SH" ] || die "$COLIMA_TEST_SH not found, so the test Docker VM cannot be used. Nothing was built (this script never builds on the main VM)."
WHY=$(bash "$COLIMA_TEST_SH" check 2>&1) || die "the test Docker VM is not available. Nothing was built: $WHY"
TEST_DOCKER_HOST=$(bash "$COLIMA_TEST_SH" docker-host) || die "colima-test.sh could not name the test Docker VM's socket. Nothing was built."
# An empty DOCKER_HOST means Docker's DEFAULT daemon, the main VM: so anything but a real socket address stops here.
case "$TEST_DOCKER_HOST" in unix:///?*) ;; *) die "colima-test.sh gave '$TEST_DOCKER_HOST' as the test Docker VM's socket, not a unix:// address. Nothing was built." ;; esac
DOCKER_HOST=$TEST_DOCKER_HOST
export DOCKER_HOST
docker info >/dev/null 2>&1 || die "the test Docker VM is set up but not running ($TEST_DOCKER_HOST). Nothing was built. Start it with: $COLIMA_TEST_SH colima start"
echo "Docker: the test VM ($TEST_DOCKER_HOST)"
# On exit, success or failure: delete the build token copy, and empty the test VM's build cache (a --no-cache build of both
# forks leaves several GB of it; the main VM is never touched).
cleanup() {
    rm -f "$WORK/.env"
    if DOCKER_HOST=$TEST_DOCKER_HOST docker builder prune -af >/dev/null 2>&1; then echo "build cache on the test VM emptied"
    else echo "(could not empty the build cache on the test VM; run: DOCKER_HOST=$TEST_DOCKER_HOST docker builder prune -af)"; fi
}
trap cleanup EXIT

say "0. AWS access (IAM credentials come from the dev .env, as in every earlier deploy)"
[ -f "$DEV_ENV" ] || die "$DEV_ENV not found"
set -a; source "$DEV_ENV"; set +a
DOCKER_HOST=$TEST_DOCKER_HOST; export DOCKER_HOST   # a DOCKER_HOST in the dev .env must never move the build to another VM
export AWS_DEFAULT_REGION=$REGION AWS_REGION=$REGION
aws sts get-caller-identity >/dev/null 2>&1 || die "the AWS credentials in $DEV_ENV were rejected (run: aws sts get-caller-identity)"
aws sts get-caller-identity --query Arn --output text
[ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ] || die "GITHUB_PERSONAL_ACCESS_TOKEN not set in $DEV_ENV"

say "1. Fresh clone of main + build token (the token copy is deleted when this script exits)"
rm -rf "$WORK"
git clone -q --branch main --depth 1 https://github.com/Digital-Democracy-Project/ddp-open-states.git "$WORK"
cd "$WORK"
git log --oneline -1
cp "$DEV_ENV" .env
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${REPO%%/*}" >/dev/null

say "2. Next unused tag (ECR is immutable)"
TAGS=$(aws ecr describe-images --repository-name ddp-scrapers --region "$REGION" \
        --query 'imageDetails[].imageTags[]' --output text)
N=$(printf '%s\n' $TAGS | python3 -c "
import re, sys
nums = [int(m.group(1)) for l in sys.stdin if (m := re.fullmatch(r'v(\d+)', l.strip()))]
print(max(nums) + 1 if nums else 1)")
TAG="v$N"
IMG="$REPO:$TAG"
echo "highest existing tag: v$((N-1))  ->  building $TAG"

say "3. Build (--no-cache is required: both forks are cloned from main at build time)"
DOCKER_BUILDKIT=1 docker build --no-cache --platform linux/arm64 \
    --secret id=github_token,env=GITHUB_PERSONAL_ACCESS_TOKEN \
    -t "$IMG" -f Dockerfile . 2>&1 | tee "/tmp/deploy-$TAG.log" | tail -15
# (set -e + pipefail stops the script here if the build failed; the full log is /tmp/deploy-$TAG.log)

say "4. Verify inside the image BEFORE pushing"
docker run --rm --entrypoint /opt/venv/bin/python "$IMG" --version
docker run --rm --entrypoint pdftotext "$IMG" -v 2>&1 | head -1

echo "-- the code that will run is importable (both forks are cloned from main at build time)"
docker run --rm --entrypoint python3 "$IMG" -c \
  "import nc.bills, ut.bills, openstates.cli.text_extract, openstates.cli.update, pandas; print('imports OK')"

echo "-- end-to-end scrape smoke test: one Utah bill through the real os-update path (one request to le.utah.gov)"
OUT=$(docker run --rm --entrypoint /bin/sh "$IMG" -c \
  'os-update ut --scrape bills session=2025S2 bill_no=HB2001 --datadir /tmp/d --cachedir /tmp/c >/tmp/o.log 2>&1; \
   echo "RC=$?"; echo "SSL=$(grep -c SSLError /tmp/o.log)"; grep -m1 "bill:" /tmp/o.log' 2>&1)
echo "$OUT"
printf '%s\n' "$OUT" | grep -q '^RC=0$'   || die "UT smoke scrape did not exit 0"
printf '%s\n' "$OUT" | grep -q '^SSL=0$'  || die "UT smoke scrape hit an SSLError"
printf '%s\n' "$OUT" | grep -q 'bill: 1'  || die "UT smoke scrape did not produce 1 bill"
echo "-- the core commit the image records (OPEN-579; compared with api-v3's by check-core-pin-drift.py)"
CORE=$(docker run --rm --entrypoint cat "$IMG" /opt/openstates-core/DDP_CORE_COMMIT)
printf '%s\n' "$CORE" | grep -Eq '^[0-9a-f]{40}$' || die "the image has no core commit record (got: $CORE)"
echo "openstates-core $CORE"
echo "all image checks passed"

say "5. Push $IMG"
docker push "$IMG" | tail -3

say "6. Going live: register a new task-definition revision pointing at $TAG"
echo "ddp-sync launches the families 'ddp-scrapers' (collection, probe) and 'ddp-scrapers-db' (load, archive; OPEN-639),"
echo "which ECS resolves to the LATEST ACTIVE revision, so the next launched task uses $TAG once both are registered."
echo "Tasks currently running on the cluster:"
aws ecs list-tasks --cluster "$CLUSTER" --region "$REGION" --query 'taskArns' --output text \
    || echo "(could not list running tasks, likely no ecs:ListTasks permission; continuing, this list is informational only)"
if [ "${CONFIRM:-}" = "1" ]; then   # opt-in prompt; the default follows the runbook and just registers
    read -r -p "Register the new revision now? [y/N] " ans
    [ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "Not registered. $TAG is pushed and verified."; exit 0; }
fi
aws ecs describe-task-definition --task-definition ddp-scrapers --region "$REGION" \
    --query taskDefinition > /tmp/taskdef-current.json
# OPEN-639: the load and archive tasks run from their own family, ddp-scrapers-db, the only one that may carry the
# database login. It does not exist before the first release with this script; the step below creates it only when
# AWS says exactly that, and stops on any other failure (an access or network error must never rebuild it and lose
# its secret).
set +e
aws ecs describe-task-definition --task-definition ddp-scrapers-db --region "$REGION" \
    --query taskDefinition > /tmp/taskdef-db-current.json 2> /tmp/taskdef-db-describe.err
echo $? > /tmp/taskdef-db-describe.rc
set -e
TAG="$TAG" python3 - <<'EOF'
import copy, json, os, re

DB_FAMILY = 'ddp-scrapers-db'
SECRET_NAMES = {'RDS_USERNAME', 'RDS_PASSWORD'}
ADDRESS_NAMES = ('RDS_HOST', 'RDS_PORT', 'RDS_DBNAME')
DROP = ['taskDefinitionArn', 'revision', 'status', 'requiresAttributes', 'compatibilities',
        'registeredAt', 'registeredBy', 'deregisteredAt']


def next_revision(td):
    """The current revision with the new image tag and ECS's read-only fields removed."""
    td = copy.deepcopy(td)
    c = td['containerDefinitions'][0]
    print(td['family'] + ': previous image', c['image'])
    c['image'] = c['image'].rsplit(':', 1)[0] + ':' + os.environ['TAG']
    for k in DROP:
        td.pop(k, None)
    return td, c


def carries_login(c):
    """Any RDS_* name or DATABASE_URL, as a secret or a plain setting (ECS exposes both as environment variables)."""
    names = [x['name'] for x in c.get('secrets', []) + c.get('environment', [])]
    return any(n.startswith('RDS_') or n == 'DATABASE_URL' for n in names)


def name_list(var):
    """A comma-separated list of variable names from the environment (names only, never values)."""
    names = [n.strip() for n in os.environ.get(var, '').split(',') if n.strip()]
    if not all(re.fullmatch(r'[A-Z][A-Z0-9_]*', n) for n in names):
        raise SystemExit(var + ' has an entry that is not a variable name like VA_API_KEY (the entry is not printed)')
    if len(set(names)) != len(names):
        raise SystemExit(var + ' names the same entry twice')
    return names


def names_in(c, key):
    return {x['name'] for x in c.get(key, [])}


current = json.load(open('/tmp/taskdef-current.json'))
main, main_c = next_revision(current)
# OPEN-639: collection and probe tasks fetch and parse outside websites and never touch the database, so the
# ddp-scrapers family must never hold the login (ECS injects a definition's secrets into every task started from it).
if carries_login(main_c):
    raise SystemExit('ddp-scrapers carries RDS_* or DATABASE_URL entries; they belong on ' + DB_FAMILY +
                     ' only (OPEN-639). Remove them from ddp-scrapers before releasing.')

if open('/tmp/taskdef-db-describe.rc').read().strip() == '0':
    db, db_c = next_revision(json.load(open('/tmp/taskdef-db-current.json')))
elif not re.search(r'\(ClientException\) when calling the DescribeTaskDefinition operation: '
                   r'Unable to describe task definition\.\s*\Z', open('/tmp/taskdef-db-describe.err').read()):
    raise SystemExit('could not read ' + DB_FAMILY + ' (not a "does not exist" answer), so it is not rebuilt: ' +
                     open('/tmp/taskdef-db-describe.err').read().strip()[-300:])
else:
    created = copy.deepcopy(current)
    created['family'] = DB_FAMILY
    db, db_c = next_revision(created)
    print(DB_FAMILY + ': not registered yet; created from ddp-scrapers (same image, roles, size and logs)')

# OPEN-633 (D2): the load and archive tasks read the RDS login from their task definition's own secret instead of a
# DATABASE_URL launch variable. Every revision is copied from the current one, so once these entries exist they
# carry forward on every later image. They are added (or replaced) only when TASK_RDS_SECRET_ARN is given, together
# with the three fixed address values, and only ever on the DB family (OPEN-639). The execution role must already
# be allowed to read that secret (an IAM step, done first).
arn = os.environ.get('TASK_RDS_SECRET_ARN', '')
if arn:
    addr = {k: os.environ.get('TASK_' + k, '') for k in ADDRESS_NAMES}
    missing = [k for k, v in addr.items() if not v]
    if missing:
        raise SystemExit('TASK_RDS_SECRET_ARN is set but TASK_' + '/TASK_'.join(missing) + ' is not')
    if not db.get('executionRoleArn'):
        raise SystemExit(DB_FAMILY + ' has no execution role, so ECS cannot read the secret')
    want = {'RDS_USERNAME': arn + ':username::', 'RDS_PASSWORD': arn + ':password::'}
    db_c['secrets'] = [x for x in db_c.get('secrets', []) if x['name'] not in want] + \
                      [{'name': k, 'valueFrom': v} for k, v in want.items()]
    db_c['environment'] = [x for x in db_c.get('environment', []) if x['name'] not in addr] + \
                          [{'name': k, 'value': v} for k, v in addr.items()]
    print(DB_FAMILY + ': RDS secret entries set (RDS_USERNAME, RDS_PASSWORD, RDS_HOST, RDS_PORT, RDS_DBNAME)')
# OPEN-880: scraper API keys (read only by collection scrapers) do not belong in plain settings. On ddp-scrapers each
# named entry becomes a secrets entry (valueFrom = TASK_<NAME>_SECRET_ARN, one secret per name) and the plain entry is
# dropped; later revisions copy the secrets entry forward (next_revision copies the whole definition). Names and
# ARN variable names only are printed, never a value.
to_secret = name_list('COLLECTION_PLAIN_TO_SECRET')
report = []  # printed only once every refusal below has passed, so a refused release never reads as a success
no_arn = ['TASK_' + n + '_SECRET_ARN' for n in to_secret if not os.environ.get('TASK_' + n + '_SECRET_ARN')]
if no_arn:
    raise SystemExit('COLLECTION_PLAIN_TO_SECRET names an entry without its secret: set ' + ', '.join(no_arn))
# The value is ECS's valueFrom: a Secrets Manager ARN (the whole secret), or <arn>:<json-key>:: (one key of a
# multi-key secret, non-empty key). Only the variable name is reported.
bad_arn = ['TASK_' + n + '_SECRET_ARN' for n in to_secret if os.environ.get('TASK_' + n + '_SECRET_ARN') and not
           re.fullmatch(r'arn:aws[a-z-]*:secretsmanager:[a-z0-9-]+:\d{12}:secret:[A-Za-z0-9/_+=.@!-]+'
                        r'(:[^:\s]+::)?', os.environ['TASK_' + n + '_SECRET_ARN'])]
if bad_arn:
    raise SystemExit(', '.join(bad_arn) + ' is not a Secrets Manager ARN, or ARN:json-key:: (the value is not printed)')
if to_secret:
    moved = [n for n in to_secret if n in names_in(main_c, 'environment')]
    main_c['secrets'] = [x for x in main_c.get('secrets', []) if x['name'] not in to_secret] + \
                        [{'name': n, 'valueFrom': os.environ['TASK_' + n + '_SECRET_ARN']} for n in to_secret]
    main_c['environment'] = [x for x in main_c.get('environment', []) if x['name'] not in to_secret]
    report = ['ddp-scrapers: secrets entries set for ' + ', '.join(to_secret) + '; plain entry removed for: ' +
              (', '.join(moved) or '(none were present)')]
both = sorted(names_in(main_c, 'environment') & names_in(main_c, 'secrets'))
if both:
    raise SystemExit('ddp-scrapers would end with a plain value and a secret for the same name (' + ', '.join(both) +
                     '); remove the plain entry (OPEN-880)')

# OPEN-880: the load and archive tasks never read the scraper API keys, so named plain entries are removed from the DB
# family only (default none). A name still on the DB family afterwards (a secrets entry cannot be removed here) refuses.
drop = name_list('DB_DROP_PLAIN_ENV')
if drop:
    gone = [n for n in drop if n in names_in(db_c, 'environment')]
    db_c['environment'] = [x for x in db_c.get('environment', []) if x['name'] not in drop]
    left = sorted(n for n in drop if n in names_in(db_c, 'environment') | names_in(db_c, 'secrets'))
    if left:
        raise SystemExit(DB_FAMILY + ' still has ' + ', '.join(left) + ' after the removal was requested (OPEN-880)')
    report.append(DB_FAMILY + ': plain entries removed: ' + (', '.join(gone) or '(none were present)'))
print(*report, sep='\n') if report else None
for td, c in ((main, main_c), (db, db_c)):
    have = {x['name'] for x in c.get('secrets', [])}
    print('RDS secret in ' + td['family'] + ':', 'yes' if SECRET_NAMES <= have else 'no')
json.dump(main, open('/tmp/taskdef-register.json', 'w'), indent=2)
json.dump(db, open('/tmp/taskdef-db-register.json', 'w'), indent=2)
EOF
# The DB family first: ddp-sync uses it only for load and archive, so if the second registration fails the
# collection tasks are still on the previous image, and the printed rollback undoes the first.
DB_REV=$(aws ecs register-task-definition --region "$REGION" --cli-input-json file:///tmp/taskdef-db-register.json \
        --query 'taskDefinition.revision' --output text)
echo "registered ddp-scrapers-db:$DB_REV (rollback: aws ecs deregister-task-definition --region $REGION --task-definition ddp-scrapers-db:$DB_REV)"
REV=$(aws ecs register-task-definition --region "$REGION" --cli-input-json file:///tmp/taskdef-register.json \
        --query 'taskDefinition.revision' --output text)

say "DONE: $TAG pushed, task-definition revisions ddp-scrapers:$REV and ddp-scrapers-db:$DB_REV registered"
echo "Tell Claude:   tag $TAG, revision $REV (db $DB_REV), core $CORE"
echo "Core check:    cd ~/Developer/repos/ddp-open-states && DOCKER_HOST=$TEST_DOCKER_HOST python3 check-core-pin-drift.py --image $IMG"
echo "               (DOCKER_HOST: the image is on the test VM, not the main one; without it the check would pull it into the main VM)"
echo "               (fails until both api-v3 copies are rebuilt on core $CORE; RUNBOOK -> api-v3 release)"
echo "ddp-sync:      EC2's ddp-sync loads cloud scrapes with its own core: rebuild it with DDP_CORE_SHA=$CORE (SYNC-180)"
echo "               and DDP_SCRAPERS_SHA=<this image's scrapers commit> (SYNC-188; RUNBOOK -> Scrapers image release)"
echo "Rollback:      aws ecs deregister-task-definition --region $REGION --task-definition ddp-scrapers:$REV"
echo "               aws ecs deregister-task-definition --region $REGION --task-definition ddp-scrapers-db:$DB_REV"
