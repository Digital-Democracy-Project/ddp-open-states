# Reply: prod `people` folder switched to our fork (OPEN-342), done 2026-10-14 01:57 UTC; first-proof checks still pending

From: prod agent (EC2 broker host, ip-172-31-78-173). The operator told me Ramon's go was given; I did not see it recorded on OPEN-342 myself, so please check it is on the ticket. Nothing else was changed (no flags turned on or off, no other remote, branch or folder touched).

## 1. Section 2 findings (read-only, done 01:53 to 01:55 UTC, before the switch)
1. Folder: `/opt/ddp-open-states/people` is the folder. The broker `web`, `celery` and `celery-beat` containers all mount it at `/opt/openstates-people`; `run-people-refresh.sh` does `cd .../people`. (The host's own `/opt/openstates-people` is a different, old directory from June 18 that nothing uses.) Remotes before: `origin` = `https://github.com/openstates/people.git` (public), `ddp` = `https://github.com/Digital-Democracy-Project/people.git` (the fork). `git status -sb`: `## main...origin/main`.
2. `remote.origin.fetch` = exactly `+refs/heads/*:refs/remotes/origin/*` (one URL, no pushurl); `ddp` the same shape. So no fix was needed (unlike the Mac).
3. `ddp` existed. Read access to the fork works over both https and ssh (`ls-remote ... refs/heads/main` -> `cbc7825d02`).
4. On `main`, tree clean, no `upstream` remote.
5. HEAD `d5cc49a9e5` was an ancestor of `ddp/main` (0 ahead of it, 28 behind). Against the public repo as last fetched: 0 ahead, 0 behind.
6. `openstates_people_pull` is registered on this host (log `registered sync_time=03:00` on 2026-10-11 21:00:57 UTC; I turned `OPENSTATES_PEOPLE_PULL_ENABLED=true` on here on 10-10, in the SYNC-102 deploy). It ran `starting`/`done` at 03:00 UTC on 10-12 and 10-13, `head_after=d5cc49a9e5` both times. `FORK_UPSTREAM_CHECK_ENABLED` is not set. I changed neither.

## 2. The switch
Saved your script as a file, read it, ran `bash <file>`. No `run-scrape` and no people refresh running. 01:57:26 to 01:57:41 UTC, exit 0.
- **Previous HEAD: `d5cc49a9e5bc70e22f0ab0273842973fc1b144fa`** (saved in `~/people-switch-previous-head.txt` on this host; please also record it on OPEN-342, I cannot reach Jira from here).
- Final output: `switched`; `origin https://github.com/Digital-Democracy-Project/people.git`; `upstream https://github.com/openstates/people.git`; `## main...origin/main`; **commits ahead of origin/main: 0**.
- Fast-forward `d5cc49a9e5..cbc7825d02`, **13 files changed, 169 insertions, 12 deletions**: 9 legislator YAML files plus `.codebot/Dockerfile`, `.codebot/test.sh`, `.github/workflows/lint-yaml.yml` and `README.md`. (The same 13 as on the Mac.)
- Re-checked after: HEAD `cbc7825d02` = `origin/main`, tree clean.
- Observation, not a problem I found: the folder now holds a `.codebot/` directory and a workflow file that are not data. I did not check whether anything that reads the folder would trip over them; the broker's import reads legislator YAML.
- The script's `git pull --ff-only` also fetched all of the fork's branches (a long list of `[new branch]` lines); that is just a fetch, not a checkout.

## 3. Still to come (I will add a second note with the results)
- **Next people pull: 2026-10-14 03:00 UTC.** `openstates_people_pull` is registered here, so I expect `done` with `head_after` = `cbc7825d02` (or the fork's `main` if it has moved). That is the first proof.
- **Next roster step: the 04:00 UTC chain.** I will check for no `No YAML on disk` and no new error classes, and report.

## 4. Rollback (not needed, for reference)
`cd /opt/ddp-open-states/people; git remote rename origin ddp && git remote rename upstream origin; git branch --set-upstream-to=origin/main main; git reset --hard d5cc49a9e5bc70e22f0ab0273842973fc1b144fa`. On Ramon's word only.
