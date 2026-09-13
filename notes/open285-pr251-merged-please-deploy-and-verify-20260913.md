# OPEN-285: PR #251 merged -- please deploy and get the real verification run

Checked directly: `ddp-open-states` PR #251 (the `run-people-refresh.sh` hardcoded-Mac-path
fix) is merged (merge commit `94bb5313`, per your own Jira comment on OPEN-285). Nice catch,
and thanks for the real correction to the earlier redundancy claim.

Per your own comment, this ticket still has real, unmet criteria:

1. Deploy this fix to the EC2 host (pull `main`, restart/redeploy whatever picks up
   `run-people-refresh.sh`).
2. Let `openstates_people_refresh` actually run once for real (or trigger it manually if
   that's supported) and confirm it succeeds -- not just "no crash," but a real completed run
   (git pull + `os-people to-database`) with evidence (flow-status, Redis, or logs).
3. Only after that succeeds: remove the live legacy crontab entry
   (`17 * * * * /opt/ddp-broker-py/infra/scripts/refresh-openstates-people.sh ...`).
4. Separately, still open: either get this host's IAM role `events:ListRules`/
   `scheduler:ListSchedules` so AWS-native scheduling can actually be ruled out, or otherwise
   confirm account-wide there's no duplicate EventBridge/ECS Scheduled Task doing this job.

Once both are done for real, OPEN-285 (and then OPEN-193, per its closure rule) can close.
Let me know what you find.
