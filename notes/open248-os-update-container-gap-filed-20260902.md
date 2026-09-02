# OPEN-245 confirmed live; the os-update gap is filed as OPEN-248, escalated for a real decision

*Replies to `notes/open193-os-update-not-in-ddp-sync-container-20260902.md`.*

Good news first: confirmed session `2026` getting past the manifest check proves OPEN-245's
`v14` image is genuinely live in production, not just deployed. That closes the loop on
everything from OPEN-241 through OPEN-245.

Agreed this is a real architecture question, not a config fix -- filed **OPEN-248** with your
full diagnosis (the shebang resolving outside the mount, the Debian 11/12 mismatch, all three
options as you laid them out). Escalating the actual choice to Ramon rather than picking one
myself, same discipline as the IAM scoping question earlier tonight.

`ddp-sync` staying stopped is the right call until this is decided -- no point re-attempting
the canary against a load step that can't succeed regardless of what else is fixed. Will report
back here once there's a decision and (if code changes) a PR.
