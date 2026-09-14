# Correction to my last note: the config-override fix never reached main -- new PR up

My last note (`60b7ecf`) said "pushed to the PR" about commit `15a41da` (the 4th
config-override instance fix) and asked you to set EC2's env vars once you saw it. That
was wrong -- I didn't realize you'd already merged PR #152 (13:38:17 UTC) before I pushed
that commit to its branch (13:41:45 UTC, four minutes later). A push to an already-merged
branch does nothing for `main`; the fix was stranded, never actually shipped.

Caught it by re-reading OPEN-290's own Jira comments just now and checking the PR's real
state directly (`gh pr view 152` shows `MERGED`, its final commit list doesn't include
`15a41da`; `git merge-base --is-ancestor 15a41da origin/main` confirms it's not an
ancestor of `main`).

**Fixed**: cherry-picked the same commit cleanly onto current `main`, opened
https://github.com/Digital-Democracy-Project/ddp-sync/pull/153. Full suite: 1250 passed.

**Please hold off setting/verifying EC2's `LEGBOT_SCRAPE_COMPLETION_TRIGGER_*` env vars
until #153 merges** -- the code that would read them isn't live on `main` yet, so setting
them now would still have zero effect. Sorry for sending you chasing a fix that wasn't
actually there.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
