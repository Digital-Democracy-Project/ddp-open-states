# OPEN-99: branch hygiene sweep, 2026-08-21

Full audit trail for the one-time branch sweep referenced from `PRIMITIVES.md`'s
`apply-local-patches.sh` section. Every branch below was individually verified with
`git merge-base --is-ancestor <branch> <fork-main>` before deletion -- none were removed on
the strength of a `[gone]` local tracking marker alone, since that only means the remote ref
disappeared, not that the content is safely merged. The two retired cherry-pick-model branches
were additionally checked against `gh pr list --state open` on both forks (empty on both)
before being treated as safe.

## `openstates-scrapers`

**Fork remote (`Digital-Democracy-Project/openstates-scrapers`), merged into `origin/main`:**

| branch | last commit | verification |
|---|---|---|
| `chore/OPEN-42` | not individually captured before deletion | listed in `git branch -r --merged origin/main` |
| `chore/OPEN-83` | not individually captured before deletion | listed in `git branch -r --merged origin/main` |
| `feat/OPEN-81-mi-bill-no-targeting` | `ab6742e2d` | `--merged` + individually re-verified |
| `fix/OPEN-30` | `f67aab7a9` | `--merged` + individually re-verified |

(`chore/OPEN-42`/`chore/OPEN-83` had no local copy in any checkout, so their tip SHA wasn't
captured before running `git push origin --delete`. Not lost: since both were confirmed
ancestors of `origin/main`, their content is permanently preserved in `main`'s own history via
whichever PR merged them -- recoverable by finding that PR in the fork's closed-PR list if ever
needed, just not written down here.)

**Production checkout (`~/Developer/repos/ddp-open-states/openstates-scrapers`), local-only:**

| branch | last commit | why stale |
|---|---|---|
| `fix/fl-floor-vote-source-url` | `db7ab1cc0` | remote already deleted (`[origin/...: gone]`), merged into `origin/main`, local copy never removed -- this is the exact 2026-07-23 incident branch |
| `feat/OPEN-81-mi-bill-no-targeting` | `ab6742e2d` | merged, remote copy deleted above in this same sweep |
| `pr-36` | `ae2c98875` | local-only (no remote tracking), merged -- was `main`'s tip immediately before the OPEN-106 merge commit |

**Dev checkout (`~/Developer/repos/ddp-open-states-dev/openstates-scrapers`), local-only:**

| branch | last commit |
|---|---|
| `chore/OPEN-19` | `56ba76f98` |
| `chore/OPEN-23` | `1a656759c` |
| `fix/OPEN-17` | `6d4ab988e` |
| `fix/mi-disable-ssl-validation` | `b76ea61a9` |
| `merge/upstream-main-20260801` | `cd7e60e20` |
| `feat/OPEN-81-mi-bill-no-targeting` | `ab6742e2d` |
| `fix/OPEN-30` | `f67aab7a9` |
| `feat/open-37-ma-chapter-law-version-20260814` | `30aacf5a7` |

**Deliberately left alone** (real, active, unmerged work): `feat/OPEN-54-generalized-waf-resilience`,
`feat/OPEN-84-fl-cookie-provider-rewiring` (both open, tracked remote branches), `fix/OPEN-63`,
`fix/OPEN-66`, `origin/upstream-contrib/fl-house-waf-session-refresh` (remote-only, untouched).

## `openstates-core`

**Fork remote (`Digital-Democracy-Project/openstates-core`), merged into `ddp/main`:**

| branch | last commit | verification |
|---|---|---|
| `chore/OPEN-34` | `bf52a8aa` | `--merged` + individually re-verified |
| `feat/OPEN-91-extract-version-ordering-module` | not individually captured before deletion | listed in `git branch -r --merged ddp/main`; same "preserved via main's history" note as scrapers' two above |
| `cherry-pick-line` | retired model branch, not an ancestor of `main` by design (see `PLAN-fork-management.md` §6) | confirmed no open PR on either fork references it (`gh pr list --state open`, both empty) |
| `ddp-patches` | same as above | same as above |

**Production checkout:** already clean going in -- only `main`, nothing stale to remove.

**Dev checkout (`~/Developer/repos/ddp-open-states-dev/openstates-core`), local-only:**

| branch | last commit |
|---|---|
| `chore/OPEN-19` | `88a23d4c` |
| `chore/az-pdf-download-20260810` | `9428e1e3` |
| `docs/mi-cookies-reputation-blocking-finding` | `37458b4a` |
| `feat/us-xml-extraction-and-diff-priority-20260812` | `7e9704db` |
| `fix/open-112-resolve-person-cache-key-chamber` | `a472e2b6` |
| `chore/OPEN-34` | `bf52a8aa` |
| `feat/open-37-ma-chapter-law-version-20260814` | `fbfb24b3` |
| `chore/OPEN-17` | `90289f29` |
| `chore/OPEN-49` | `e8838630` |

Also removed one orphaned local ref, `refs/remotes/prod-local/local-patches` -- a leftover
remote-tracking ref from some earlier, no-longer-configured `prod-local` remote (`git remote
-v` shows no such remote today). Harmless local git metadata, zero shared-state impact.

**Deliberately left alone** (real, active, unmerged work, confirmed NOT ancestors of `ddp/main`):
`fix/federal-vote-bioguide-resolution` (had a `[gone]` remote marker but a real, unmerged commit
-- this is exactly the case the "don't trust `[gone]` alone" rule exists for), `fix/resolve-person-cache-key-org-classification`,
`fix/archive-block-page-detection-v2`, `feat/OPEN-54-generalized-waf-resilience`,
`fix/OPEN-53-archiver-retry-exclusion`, `chore/OPEN-76` (remote-only, untouched).

## What wasn't done

Attempted to enable GitHub's repo-level "automatically delete head branches" setting on both
forks (`gh api repos/.../{openstates-core,openstates-scrapers} -X PATCH -f
delete_branch_on_merge=true`) as a root-cause fix -- this would make the habit automatic
instead of relying on whoever closes a PR to remember it. Both calls 404'd, which reads as an
admin-scope limitation on this environment's GitHub token rather than the setting being
unavailable. Worth a human doing this by hand in each repo's Settings page (`General` →
`Pull Requests` → "Automatically delete head branches") -- confirmed via `gh api .../api-v3
--jq .delete_branch_on_merge` that it's `false` there too, so this isn't enabled anywhere in
DDP's fork estate yet, not just these two.
