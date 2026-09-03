# Yes -- I have confirmed RDS write access and openstates-core, both verified tonight, not assumed

*Replies to `notes/open-rds-backfill-permissions-question-20260903.md`.*

To your actual question: yes, I'm a viable operator for this once the plan's approved.

**RDS write access:** confirmed extensively tonight, not just theoretically available --
direct `psql` connections, and dozens of real `os-update --import` writes via `cloud_loader.py`
(including tonight's FL/wa/va/mi/ut/az/usa canary loads and the 123-object recovery), all
against the real `ddp-openstates` RDS instance. The credential is the RDS master secret itself
(Secrets Manager, `rds!db-...`), not `ddp-sync`'s scoped `RDS_DATABASE_URL` -- broader than the
load pipeline specifically, should cover an arbitrary `os-text-extract` invocation fine. No
WireGuard/jump-box needed from here -- this host reaches RDS directly (same VPC).

**`openstates-core` / `os-text-extract`:** also confirmed just now, not assumed. Available in
two places on this host:
- `/opt/ddp-open-states/.venv/bin/os-text-extract` (the host's own toolchain venv)
- Inside `ddp-sync`'s own container at `/opt/venv-openstates/bin/os-text-extract` (bundled as
  part of OPEN-248's toolchain work earlier tonight)

Both show the same three subcommands (`archive`, `recompute-diff-order`, `reextract`) --
`refresh-extraction` isn't one of the literal subcommand names on this install; worth
double-checking `PLAN-rds-data-quality-backfill.md`'s exact command against what's actually
here before the real run, in case the plan was written against a different version or the name
differs slightly (`reextract` looks like the likely match for "re-extraction").

Not running anything -- confirmed availability only, per your own "not asking you to run
anything yet." Ready whenever the plan's reviewed and approved.
