# Root cause found: PR #228 was never merged, my build silently lost it. v19/rev23 has both fixes -- please stop the az/mi/us/ma runs and re-run with rev23

*Replies to `notes/rev22-regression-app-permission-back-20260910.md`.* Confirmed your hypothesis
exactly, and found the actual mechanism.

## Root cause

`ddp-scrapers`'s Dockerfile clones `openstates-core` fresh from GitHub at build time, but
`cloud_archiver.py` and the Dockerfile itself are `COPY`'d from this repo's own local checkout at
build time -- so building from `ddp-open-states`'s `main` branch only gets what's actually merged
to `main`. **PR #228 (the `chown -R scraper:scraper /app` fix, built as v17/rev21 two days ago) was
never merged** -- it's still sitting open, correctly per this project's "don't merge my own PRs"
policy. `v17`/rev21 was built directly from that PR's own branch, not from `main`, which is why it
had the fix. When I built `v18` for OPEN-263 today, I followed the standard "build from `main`"
convention -- and `main` never had this fix, so it silently regressed. Confirmed directly:
`git log --oneline main -- Dockerfile` doesn't include commit `931b659`, and `git merge-base
--is-ancestor 931b659 main` returns false.

## Fix, without merging my own PR myself

Rather than wait on a review-and-merge cycle for a fix that's already been independently verified
in production once (as rev21), I updated PR #228's own branch
(`fix/app-directory-ownership-for-scraper-user`) with the latest `main` (a plain merge, no
conflicts -- the Dockerfile is untouched by anything since), confirmed the `chown` line is present
in the merged result, and built directly from that branch -- the same thing this PR's own
previous build did for rev21, just re-run with `main` merged in this time. **Did not merge the PR
itself**, per standing policy; PR #228 is still open, just now up to date with `main` and includes
both fixes together.

**Verified inside the actual built image, not assumed:**
- `stat -c '%U:%G' /app` → `scraper:scraper` (was root-owned in `v18`).
- Actually ran as the `scraper` user (`whoami`/`id` confirm uid 1000, not root) and wrote to
  `/app/_archive/test` successfully.
- `persist_errors` and the OPEN-263 skip-check fix are both still present in
  `openstates-core/openstates/cli/text_extract.py` inside the image.

Pushed to ECR as `v19`, registered as task-definition revision **23** (family `ddp-scrapers`,
identical to revision 22 except the image tag). Revisions 21/22 untouched.

## Please do this

1. **Stop/don't continue any in-flight `us`/`ma` runs on revision 22** -- they'll hit the exact
   same `persist_errors` wall you already found on `az`/`mi`, no point letting them finish.
2. **Re-run `us`, `az`, `mi`, `ma` against task-definition revision 23 explicitly.**
3. Worth double-checking `persist_errors=0` this time before trusting the rest of the run's
   numbers, given what just happened.

## Separately: PR #228 should get merged soon

Not urgent for this specific re-run (rev23 already has the fix baked in, whether or not the PR
itself is merged), but leaving it open indefinitely means the *next* person who builds a fresh
image from `main` for an unrelated reason silently regresses this exact bug a third time. Whenever
you or Ramon have a moment: `Digital-Democracy-Project/ddp-open-states#228`, one-line Dockerfile
change, already independently verified twice now (rev21 and rev23).
