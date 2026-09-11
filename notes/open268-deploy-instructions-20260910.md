# OPEN-268 deploy instructions -- both PRs merged, this closes the acceptance criteria

Both PRs are merged (`ddp-open-states` #235 into `main` @ `97441da`, `ddp-sync` #130) --
verified independently by you already per the Jira comments. What's left is exactly the two
things flagged as not-done-on-purpose in both PR bodies: build/push/register the new image,
then one supervised dry-run trial.

## 1. Build and push the new `ddp-open-states` image (v21)

Same sequence as the earlier Python 3.10 deploy this session (`v20`/revision 24) -- this is
additive, revision 24 stays live and untouched until you explicitly point something at 25.

```bash
# Fresh clone of main (now includes cloud_text_extract.py, PR #235)
git clone --branch main --depth 1 \
    https://github.com/Digital-Democracy-Project/ddp-open-states.git /tmp/ddp-open-states-deploy
cd /tmp/ddp-open-states-deploy
cp ~/Developer/repos/ddp-open-states-dev/.env .env   # or wherever your GITHUB_PERSONAL_ACCESS_TOKEN lives
set -a && source .env && set +a

aws ecr get-login-password --region us-east-1 | docker login --username AWS \
    --password-stdin 350941939790.dkr.ecr.us-east-1.amazonaws.com

DOCKER_BUILDKIT=1 docker build --no-cache --platform linux/arm64 \
    --secret id=github_token,env=GITHUB_PERSONAL_ACCESS_TOKEN \
    -t 350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v21 \
    -f Dockerfile .

# Sanity check before pushing: confirm cloud_text_extract.py actually made it in and works
docker run --rm --entrypoint /opt/venv/bin/python \
    350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v21 --version
docker run --rm -e RUNNER_SCRIPT=cloud_text_extract.py \
    350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v21 --help
# ^ should print os-text-extract's own --help (proves the execvp passthrough actually reaches it)

docker push 350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v21
```

## 2. Register task-definition revision 25

Identical to revision 24 except the image tag -- everything else (env vars, role ARNs, log
config, ARM64 runtime, network mode) stays the same:

```bash
aws ecs describe-task-definition --task-definition ddp-scrapers --query taskDefinition \
    > /tmp/taskdef24.json
python3 -c "
import json
td = json.load(open('/tmp/taskdef24.json'))
td['containerDefinitions'][0]['image'] = td['containerDefinitions'][0]['image'].replace(':v20', ':v21')
for key in ['taskDefinitionArn','revision','status','requiresAttributes','compatibilities','registeredAt','registeredBy','deregisteredAt']:
    td.pop(key, None)
json.dump(td, open('/tmp/taskdef25-register.json', 'w'), indent=2)
"
aws ecs register-task-definition --cli-input-json file:///tmp/taskdef25-register.json \
    --query "taskDefinition.{arn:taskDefinitionArn,revision:revision,image:containerDefinitions[0].image}"
```

## 3. The supervised dry-run canary (OPEN-268's second acceptance criterion)

Via `ddp-sync`'s new trigger endpoint (PR #130) -- pick a small jurisdiction, `mode=dry-run`
only, do NOT use `mode=commit` for this first trial:

```bash
curl -X POST "http://localhost:8000/trigger/openstates-backfill/mi?subcommand=recompute-diff-order&mode=dry-run" \
    -H "Authorization: Bearer $DDP_SYNC_API_KEY"
```

That returns `{"status": "started", "run_id": "...", ...}` immediately (202). The actual result
(the dry-run summary line, or a failure) lands a bit later in `ddp-sync`'s own structured
logs -- grep for the `run_id` from the response, e.g.:

```bash
grep '"run_id": "<the run_id from the response>"' <ddp-sync log path>
```

**What "success" looks like**: a log line `openstates_backfill: fargate task done` with a
non-empty `output` field containing MI's usual dry-run summary shape (e.g. `mi: [DRY RUN] N
bills checked | unchanged=... corrected=... nulled=...`), matching what you'd get running
`os-text-extract recompute-diff-order mi --dry-run` directly. If that matches, the whole
OPEN-268 surface is proven end-to-end and you can move it to Done.

**What to watch for specifically** (things pm-review flagged and I fixed, worth confirming for
real rather than just trusting the unit tests): the log-fetch logic needs 2 consecutive quiet
CloudWatch rounds before it returns, so expect the `output` to arrive maybe 4-10 seconds after
the task itself reports done in `DescribeTasks` -- if `output` comes back empty even though the
task's `exit_code` was 0, that's worth flagging back rather than assuming it's fine, since it'd
mean the log-fetch fix doesn't hold up against real CloudWatch timing the way the unit tests'
fake client predicted.

## Rollback

If anything goes wrong: task-definition revision 24 (image `v20`) is untouched and still the
one anything not explicitly pointed at 25 will keep using. No config anywhere defaults to the
new revision automatically.
