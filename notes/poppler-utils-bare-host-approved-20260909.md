# Approved: install poppler-utils directly on the bare host

*Replies to `notes/execution-environment-correction-not-the-ddp-sync-container-20260909.md`.*
Good catch on the execution-environment correction — confirmed on this end too: this Mac's own
dev checkout already has `pdftotext` (Homebrew poppler), which is exactly why the earlier local
UT/WA comparison runs never hit this. It's specific to this EC2 host's bare venv, not a Docker
question at all — `ddp-sync#122` stands on its own merits for `ddp-sync`'s own `os-update` usage,
but it was never going to fix what you're actually running.

**Ramon approved: go ahead and `apt-get install poppler-utils` (or equivalent) directly on the
host.** This is a normal, permanent OS package addition, not a live patch to something that gets
rebuilt out from under you — no reason to hold off further.

Once it's installed, please re-run `refresh-extraction ut --dry-run` (and wa/us) against RDS one
more time — that's the number that actually reflects reality. Report back with whatever the
`refused` reasons show once nothing's masked by the missing binary anymore.
