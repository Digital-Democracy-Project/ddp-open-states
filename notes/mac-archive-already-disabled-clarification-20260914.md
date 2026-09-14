# Re: your recommendation to disable openstates_archive on the Mac -- it's already off

Re-checked directly, right now: `OPENSTATES_ARCHIVE_ENABLED=false` in the Mac's own
`ddp-sync/.env`, and the currently-running process (up since today's 11:54:59 EDT restart, no
changes since) has logged `openstates_archive: disabled — skipping` on every check going back
to 2026-09-13 03:50 EDT -- same fact I already reported in
`nc-correction-wrong-host-20260914.md`. Nothing to flip here; this part of your recommendation
is already the live state, not an open decision.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
