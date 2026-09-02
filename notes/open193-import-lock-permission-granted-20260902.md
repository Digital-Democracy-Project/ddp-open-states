# Import-lock write permission granted — both load-stage blockers should now be clear

*Replies to `notes/open245-no-op-manifest-fix-pr221-20260902.md`.*

Ramon added the narrowly-scoped `s3:PutObject` statement to the EC2 role:

```json
{
    "Sid": "ImportLockWrite",
    "Effect": "Allow",
    "Action": "s3:PutObject",
    "Resource": "arn:aws:s3:::ddp-openstates-scraper-memory/prod/*/_import_lock"
}
```

Scoped to `_import_lock` marker objects only, under this environment's `prod/` prefix — the
role's existing read-only S3 access is otherwise unchanged.

**Both known load-stage blockers should now be cleared:**
- OPEN-245 (no-op sessions lacking a manifest) — merged once PR #221 lands; not merged yet.
- The import-lock `AccessDenied` (real sessions) — should be resolved by the permission above,
  effective immediately.

Please pull `ddp-sync`'s latest `main` if PR #221 has merged by the time you see this, restart,
and re-attempt the full 4-session FL canary. If it clears end to end this time, that closes out
OPEN-193 item 4.
