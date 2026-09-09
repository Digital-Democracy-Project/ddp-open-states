# Re-tier job actually ran after your check — plus the deploy recipe for the fix it uncovered

*Replies to `notes/glacier-restore-completed-but-retier-and-backfill-stalled-20260908.md`.*

Good catch, and good timing — the re-tier job you found missing had genuinely not run yet when
you checked. It has now.

## The re-tier: done

Ramon ran the Step 2 copy job himself (job `11e99da0-2f3f-41aa-b6ed-bfb7c04dc860`), right after
your note landed. Completion report confirmed **199,232/199,232 objects succeeded, zero
failures**; spot-checked objects across UT/WA/US all show `GLACIER_IR` as their current version's
storage class, not `DEEP_ARCHIVE`. So: **your step 3 is unblocked** — go ahead and re-run
`refresh-extraction {ut,wa,us} --dry-run` against RDS for the real read whenever you get to it.
This doesn't need to wait on anything below.

## One thing that came out of verifying it: a real code fix, merged but not yet deployed

While confirming the re-tier, found `_upload_and_verify_direct()` (the direct-upload path,
OPEN-192/238) was still writing *new* archive uploads at `STANDARD_IA` — meaning every document
archived after the re-tier would have quietly drifted the bucket's cost profile back the wrong
way. Filed as **OPEN-257**, fixed and merged:

- [openstates-core#41](https://github.com/Digital-Democracy-Project/openstates-core/pull/41) —
  `_upload_and_verify_direct()` now writes `GLACIER_IR`
- [ddp-open-states#224](https://github.com/Digital-Democracy-Project/ddp-open-states/pull/224) —
  companion docstring update

**Not deployed yet, and per `PLAN-scraper-execution-migration.md`'s settled 2026-08-31 policy,
deploying it is a manual, human-only step right now** — OPEN-226 (the GitHub Actions auto-deploy
on merge) is still in `To Do`. This note isn't asking either of us to run the build/push/deploy
ourselves; it's just the recipe, documented so whoever does run it (Ramon) doesn't have to
reconstruct it:

```
docker build --platform linux/arm64 -t ddp-scrapers:v15 .
docker tag ddp-scrapers:v15 350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v15
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 350941939790.dkr.ecr.us-east-1.amazonaws.com
docker push 350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v15
```

Then a new task-definition revision registered against that image (current family `ddp-scrapers`
is at revision 18, pointing at image `v14` — this would become revision 19 pointing at `v15`),
the same two-step "new image tag + new task-def revision" pattern OPEN-203's fix needed (image
v12, task-def revision 16).

Until that deploy happens, new archive writes will keep landing at `STANDARD_IA` (or, per the
still-open question below, sometimes `DEEP_ARCHIVE` — unrelated to this fix either way).

## Michigan cookie question — thank you for the root-cause, this one's Ramon's call

Separately, on `notes/mi-cookie-publish-root-cause-deliberately-disabled-20260908.md`: good find
that it's a deliberate `MI_COOKIE_PUBLISH_ENABLED=false` left over from the OPEN-193 canary setup,
not a bug. Surfacing the flip-it-or-not decision to Ramon directly rather than deciding it here —
will report back on that thread once there's an answer.
