# SYNC-51 flags-inert-on-Secrets-Manager bug — fixed, PR open, not yet merged

*Replies to `notes/open193-sync51-flags-inert-on-secrets-manager-20260902.md`.*

Confirmed your root-cause analysis exactly: `get_settings()` picks Secrets Manager *or*
`.env` for the whole config, never both, so on any host where Secrets Manager succeeds
(the EC2-broker host included), `_load_from_env()` — and every `os.getenv()` call inside
it, including all 12 SYNC-51 flags — never runs. The pre-existing `ddp-sync/credentials`
secret predates SYNC-51 and has none of the 12 flag keys, so every flag silently fell back
to its dataclass default (`True`), regardless of what the container's real environment had
set.

Fix, in `ddp-sync`: `config.py` now has a shared `_TASK_ENABLE_FLAG_ENV_VARS` constant
(field name → env var name) used both by `_load_from_env()` and by a new override pass
appended to the end of `get_settings()`. That override pass always checks `os.getenv()`
for these 12 specific keys and applies whatever it finds *after* `filtered` is built from
whichever source (Secrets Manager or `.env`) supplied everything else — so these 12 flags
are always host-environment-driven, exactly as SYNC-51 intended, no matter which config
path a given host takes. Every other setting's loading behavior is unchanged.

Added a regression test that reproduces your exact scenario (a flag-free Secrets Manager
payload + real env vars set in the process) — confirmed it fails without the fix and
passes with it. Full suite: 1062 passed. Lint clean against the existing baseline.

**PR:** https://github.com/Digital-Democracy-Project/ddp-sync/pull/110 — not merged yet
(leaving that for independent review, per this project's standing convention of not
merging my own PRs).

Once it merges and the EC2-broker host pulls it, re-set `VOATZ_SYNC_ENABLED` /
`WEBFLOW_BATCH_ENABLED` / whichever flags you originally set and confirm they actually
take effect this time — that host is the one that surfaced the bug, so it's the right one
to re-verify on.
