# Request for the prod agent: switch prod's `people` folder to our fork. HOLD until Ramon says go. (dev side, 2026-10-13)

**STATUS: HOLD. Do not run anything in this note until Ramon's go is recorded on Jira OPEN-342 (and he has told you).** This note is the preparation. It is not the go. Reads and checks (section 2) are fine now; the switch itself (section 3) waits.

Jira: OPEN-342 (this step), OPEN-341 (the same switch on the Mac, done), OPEN-336 (the epic). Plan: `ddp-infra/PLAN-fork-management.md` section 8.3 and 8.9.

## 1. What this is, and why

Prod's `people` folder (`/opt/ddp-open-states/people`, read by the broker through the `/opt/openstates-people` mount) currently follows the **public** `openstates/people`. We now run a formal fork, `Digital-Democracy-Project/people`: the public project plus the corrected data we carry (for example the FL and role-date fixes). Until prod's folder follows the fork, prod does not get those fixes. The switch changes only where the folder looks for updates (swap two remote names) and then fast-forwards it once. No data is edited by hand.

The Mac Studio did this on 2026-10-13 (OPEN-341). Result there: folder moved from `d5cc49a9e5` to the fork's `main` (`cbc7825d02`), 13 files, 0 ahead of the fork afterwards, no uncommitted changes.

## 2. Checks to do first (read-only, safe to do before the go)

Report anything surprising in a reply note and **stop**; do not "fix" it on your own.

1. **Which folder, really.** Confirm `/opt/ddp-open-states/people` is the folder the weekly import (`run-people-refresh.sh`) and ddp-sync's `people-pull` use, and that `/opt/openstates-people` points at it. Print `git -C <folder> remote -v` and `git -C <folder> status -sb`.
2. **The odd setting we hit on the Mac.** There, `origin` was set to fetch only `main`, so the script correctly refused ("remote origin has non-default config"). Check: `git config --get-all remote.origin.fetch`. If it is not exactly `+refs/heads/*:refs/remotes/origin/*`, the script will refuse here too. The fix we used on the Mac was one line, run on the go: `git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'`. (It does not change data. A rollback of the switch would also leave origin with the normal setting; harmless.)
3. **Does a `ddp` remote exist, and can this host read the fork?** The script expects `origin` = public and `ddp` = the fork (the plan assumes this; the Mac had it). If `ddp` is missing on prod, say so; adding it is a change for you to propose, and the https address (`https://github.com/Digital-Democracy-Project/people.git`) is accepted by the script if this host has no SSH access to the fork. Test read access with `git ls-remote <fork address> refs/heads/main` (it should print one line).
4. **Working tree clean, on `main`, no `upstream` remote already.** The script refuses otherwise.
5. **HEAD is inside the fork's `main`** (the script checks this; you can pre-check with `git fetch ddp main && git merge-base --is-ancestor HEAD ddp/main && echo yes`). If it says no, prod has a commit the fork lacks; do not switch, report it.
6. **Does prod's ddp-sync run `openstates_people_pull` at all?** On the Mac it never registered until today (it was stuck behind the scrape switch, SYNC-108, fixed in ddp-sync PR 217). Check `/schedule` and the log on prod for `openstates_people_pull: registered`, and whether `OPENSTATES_PEOPLE_PULL_ENABLED` is set. **Do not turn it on**; just report. This decides what the acceptance check in section 4 can be on prod.
7. **Timing.** Do not run the switch during the 03:00 UTC people pull, the 04:00 UTC roster step, or the Sunday 10:00 UTC weekly refresh/import (if prod runs them). Any quiet time in daytime is fine.

## 3. The switch (only after the go)

By hand, never from an unattended script. Save the script as a file, read it, then run it with `bash <file>`. It makes these checks itself: not on `main`, dirty tree, an `upstream` remote already present, origin/ddp addresses not the expected ones, non-default remote config, HEAD not inside the fork. If any fails it changes **nothing**. If a later step fails it restores both remotes from the recorded addresses. It writes the old position to `~/people-switch-previous-head.txt` and prints it.

```bash
#!/usr/bin/env bash
set -eEuo pipefail

cd /opt/ddp-open-states/people

PUBLIC_OK=(https://github.com/openstates/people https://github.com/openstates/people.git git@github.com:openstates/people.git)
FORK_OK=(https://github.com/Digital-Democracy-Project/people https://github.com/Digital-Democracy-Project/people.git git@github.com:Digital-Democracy-Project/people.git)
in_list() { local x=$1; shift; for i in "$@"; do [ "$i" = "$x" ] && return 0; done; return 1; }

if ps aux | grep -q '[r]un-scrape'; then echo "a scrape is running; try again when it finishes"; exit 1; fi
[ "$(git rev-parse --abbrev-ref HEAD)" = main ] || { echo "not on main"; exit 1; }
[ -z "$(git status --porcelain)" ]               || { echo "working tree not clean"; exit 1; }
git remote get-url upstream >/dev/null 2>&1      && { echo "an 'upstream' remote already exists"; exit 1; }

pub=$(git remote get-url origin); fork=$(git remote get-url ddp)
in_list "$pub"  "${PUBLIC_OK[@]}" || { echo "origin is not the public repo: $pub"; exit 1; }
in_list "$fork" "${FORK_OK[@]}"   || { echo "ddp is not our fork: $fork"; exit 1; }
for r in origin ddp; do
  [ "$(git config --get-all remote.$r.url | wc -l | tr -d ' ')" = 1 ] \
  && [ -z "$(git config --get remote.$r.pushurl || true)" ] \
  && [ "$(git config --get-all remote.$r.fetch)" = "+refs/heads/*:refs/remotes/$r/*" ] \
  || { echo "remote $r has non-default config"; exit 1; }
done

git fetch --quiet ddp main
git merge-base --is-ancestor HEAD ddp/main || { echo "HEAD is not inside our fork's main; do not switch"; exit 1; }
old=$(git rev-parse HEAD)
echo "previous HEAD: $old   (save this for the rollback)"
echo "$old" > ~/people-switch-previous-head.txt

restore() {
  set +e; trap - ERR; echo "FAILED, restoring remotes"
  for r in origin upstream ddp; do git remote remove "$r" 2>/dev/null; done
  git remote add origin "$pub"; git remote add ddp "$fork"
  git fetch --quiet origin main; git branch --set-upstream-to=origin/main main
  exit 1
}
trap restore ERR

git remote rename origin upstream
git remote rename ddp origin
git branch --set-upstream-to=origin/main main
git pull --ff-only
trap - ERR

echo "switched"
echo "--- result"
git remote -v | awk '{print $1, $2}' | sort -u
git status -sb | head -2
echo "commits ahead of origin/main: $(git rev-list --count origin/main..HEAD)   (expect 0)"
```

Notes on this script versus the plan's: the `cd` is prod's folder; it also refuses while a `run-scrape` process runs (harmless if none exist on this host); and it prints the result at the end. If this host cannot read the fork over ssh, say so before running; do not edit the script's allowed-address lists on your own.

## 4. What "done" looks like, and what to send back

Reply with a new note in `notes/` (name it `reply-prod-people-folder-switch-...`), containing:

1. **Section 2 findings**, before the switch (items 1 to 6), including the `remote.origin.fetch` value and whether `ddp` existed.
2. **The previous HEAD** (and that `~/people-switch-previous-head.txt` exists). Also post it on OPEN-342 if you can; if not, put it in the note and Ramon will copy it.
3. **The script's final output** (the `switched` block): expect `origin` = `Digital-Democracy-Project/people`, `upstream` = `openstates/people`, and 0 ahead.
4. **Next scheduled people pull:** if `openstates_people_pull` is registered on prod, the first 03:00 UTC run after the switch should be `completed` with `head_sha_after` equal to the fork's `main`. If it is not registered on prod (item 6), say that; the Sunday 10:00 UTC weekly import then does the pull, and that is the first proof.
5. **The next roster step** (04:00 UTC chain or the weekly import) ran clean: no `No YAML on disk`, no new error classes.

## 5. Rollback (a person, on Ramon's word; it resets the checkout)

```bash
cd /opt/ddp-open-states/people
git remote rename origin ddp && git remote rename upstream origin
git branch --set-upstream-to=origin/main main
git reset --hard <previous HEAD printed by the switch>
```

The folder holds only tracked data and the clean-tree check passed first, so nothing local is lost.

## 6. Please do NOT

- Run the switch before the go is recorded.
- Turn on `FORK_UPSTREAM_CHECK_ENABLED` or `OPENSTATES_PEOPLE_PULL_ENABLED` on prod. The fork check is meant to run on the Mac only (two instances would post every alert twice). The people pull on prod is a separate question for Ramon.
- Change any other remote, branch or folder, or edit data in the folder.

## 7. Facts as of 2026-10-13 evening (they will move)

- Fork `main`: `cbc7825d02`. It carries 9 fixes (each with an `Upstream-PR:` line in its commit message). On 2026-10-13 the public project merged four of ours (Massullo, Campbell, McCluskie, Hofeld) and some DC changes, so the fork is **11 commits behind the public project** and only 5 data files differ from it. A catch-up pull request is planned once the oldest missing change is 3 days old (about 2026-10-16). This does not affect the switch: the pull is fast-forward-only to the fork's `main`.
- Nothing on the dev side needs an answer from you before the go. After the go, the reply note in section 4 is all we need.
