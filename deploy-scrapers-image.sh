#!/usr/bin/env bash
# Build, verify, push and register a new ddp-scrapers image -- the one command a human operator runs
# to deploy scraper changes to Fargate. Follows RUNBOOK.md -> "Deploying a Fargate image change".
# Run on the Mac (never the EC2 host), as yourself: it loads the AWS IAM credentials and the GitHub
# token from the dev checkout's .env, which an agent session can't be expected to read.
#
#   bash deploy-scrapers-image.sh              # verifies, pushes, then registers the new revision
#   CONFIRM=1 bash deploy-scrapers-image.sh    # same, but asks before the one step that goes live
#
# Stops at the first failed check. Nothing goes live until the final register step.
set -euo pipefail

REGION=us-east-1
REPO=350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers
CLUSTER=ddp-scrapers
WORK=/tmp/ddp-open-states-deploy
DEV_ENV="$HOME/Developer/repos/ddp-open-states-dev/.env"
say() { printf '\n==> %s\n' "$*"; }
die() { printf '\nSTOP: %s\n' "$*" >&2; exit 1; }

say "0. AWS access (IAM credentials come from the dev .env, as in every earlier deploy)"
[ -f "$DEV_ENV" ] || die "$DEV_ENV not found"
set -a; source "$DEV_ENV"; set +a
export AWS_DEFAULT_REGION=$REGION AWS_REGION=$REGION
aws sts get-caller-identity >/dev/null 2>&1 || die "the AWS credentials in $DEV_ENV were rejected (run: aws sts get-caller-identity)"
aws sts get-caller-identity --query Arn --output text
[ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ] || die "GITHUB_PERSONAL_ACCESS_TOKEN not set in $DEV_ENV"

say "1. Fresh clone of main + build token (the token copy is deleted when this script exits)"
rm -rf "$WORK"
git clone -q --branch main --depth 1 https://github.com/Digital-Democracy-Project/ddp-open-states.git "$WORK"
cd "$WORK"
git log --oneline -1
trap 'rm -f "$WORK/.env"' EXIT
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
  "import nc.bills, ut.bills, openstates.cli.text_extract, openstates.cli.update; print('imports OK')"

echo "-- end-to-end scrape smoke test: one Utah bill through the real os-update path (one request to le.utah.gov)"
OUT=$(docker run --rm --entrypoint /bin/sh "$IMG" -c \
  'os-update ut --scrape bills session=2025S2 bill_no=HB2001 --datadir /tmp/d --cachedir /tmp/c >/tmp/o.log 2>&1; \
   echo "RC=$?"; echo "SSL=$(grep -c SSLError /tmp/o.log)"; grep -m1 "bill:" /tmp/o.log' 2>&1)
echo "$OUT"
printf '%s\n' "$OUT" | grep -q '^RC=0$'   || die "UT smoke scrape did not exit 0"
printf '%s\n' "$OUT" | grep -q '^SSL=0$'  || die "UT smoke scrape hit an SSLError"
printf '%s\n' "$OUT" | grep -q 'bill: 1'  || die "UT smoke scrape did not produce 1 bill"
echo "all image checks passed"

say "5. Push $IMG"
docker push "$IMG" | tail -3

say "6. Going live: register a new task-definition revision pointing at $TAG"
echo "ddp-sync launches the family 'ddp-scrapers', which ECS resolves to the LATEST ACTIVE revision,"
echo "so the next launched task (any jurisdiction) uses $TAG once this is registered."
echo "Tasks currently running on the cluster:"
aws ecs list-tasks --cluster "$CLUSTER" --region "$REGION" --query 'taskArns' --output text
if [ "${CONFIRM:-}" = "1" ]; then   # opt-in prompt; the default follows the runbook and just registers
    read -r -p "Register the new revision now? [y/N] " ans
    [ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "Not registered. $TAG is pushed and verified."; exit 0; }
fi
aws ecs describe-task-definition --task-definition ddp-scrapers --region "$REGION" \
    --query taskDefinition > /tmp/taskdef-current.json
TAG="$TAG" python3 - <<'EOF'
import json, os
td = json.load(open('/tmp/taskdef-current.json'))
c = td['containerDefinitions'][0]
print('previous image:', c['image'])
c['image'] = c['image'].rsplit(':', 1)[0] + ':' + os.environ['TAG']
for k in ['taskDefinitionArn','revision','status','requiresAttributes','compatibilities',
          'registeredAt','registeredBy','deregisteredAt']:
    td.pop(k, None)
json.dump(td, open('/tmp/taskdef-register.json', 'w'), indent=2)
EOF
REV=$(aws ecs register-task-definition --region "$REGION" --cli-input-json file:///tmp/taskdef-register.json \
        --query 'taskDefinition.revision' --output text)

say "DONE: $TAG pushed, task-definition revision $REV registered"
echo "Tell Claude:   tag $TAG, revision $REV"
echo "Rollback:      aws ecs deregister-task-definition --region $REGION --task-definition ddp-scrapers:$REV"
