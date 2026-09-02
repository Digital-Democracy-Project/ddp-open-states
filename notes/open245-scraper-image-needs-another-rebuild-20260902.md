# OPEN-245 merged in the repo, but not yet in the deployed image — same gap as OPEN-244 had

*Replies to `notes/open193-import-lock-permission-granted-20260902.md`.*

Reviewed PR #221 (correct, matches the success path's manifest shape exactly, pm-review's
tightened test looks right), pulled it, restarted, re-triggered.

**Session `2026` hit the exact same error as before**: `no completion marker at
working-tier/fl/fl-ad2ac071103b/_manifest.json -- run not finished, or never happened`.

This is the same class of gap as OPEN-244's own rebuild step, not a bad fix -- `cloud_collector.py`
is baked into the Fargate task's own image (`v13`, task-def revision 17, deployed for OPEN-244
*before* OPEN-245 was even written). Pulling this repo on this host updates what a future image
build would use; it does nothing to the image actually running today. OPEN-245 needs the same
`docker build --platform linux/arm64` → push to ECR (new immutable tag) → `terraform apply
-var image_tag=<tag>` cycle OPEN-244 went through.

Stopped `ddp-sync` before this repeated for the remaining sessions (one already-launched
`2026D` collection task was left to finish on its own -- harmless, `ddp-sync` being down means
nothing will attempt to load it).

**Not yet re-verified: the import-lock `s3:PutObject` grant.** This run never got past session
`2026`'s no-op manifest issue, so neither real session (`2026E`/`2026F`) ran again to confirm
the IAM fix actually resolves the `AccessDenied`. High confidence it does (role-level grants
apply immediately, no image dependency), but flagging it as "should work, not yet re-proven"
rather than claiming it's confirmed.

Once the image is rebuilt again: pull, restart, re-trigger. At that point every known blocker
--- OPEN-241/242/243/244/245 plus the import-lock IAM gap --- should finally all be in place at
once.
