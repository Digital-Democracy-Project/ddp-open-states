# ddp-scrapers:v22 built and pushed (OPEN-293 fix included) -- new task-def revision 26 registered, not live yet

Built on the Mac per `RUNBOOK.md`'s "Deploying a Fargate image change" section (fresh clone of
`ddp-open-states` main, `--no-cache`, `linux/arm64`) -- not built on this host, per that
runbook's own explicit division of labor.

**Image**: `350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v22`
(`sha256:7dde9607479a60d16315127b54e874f4b62ff915af78610124b6f6060515a099`), pushed and
confirmed live in ECR.

**Verified before pushing**: `python --version` (3.10.21), `pdftotext -v` (poppler 22.12.0)
both run correctly inside the image, and confirmed directly (`grep` inside the container) that
`openstates-scrapers`'s `normalize_clerk_bill_id` (OPEN-293's fix, PR #47, merged today) is
actually present in the built image -- not just assumed from the Dockerfile's `main` branch ref.

**v22 vs v21 (currently live)**: this is a full rebuild off each repo's current `main`, not a
narrow single-fix build. The Dockerfile clones `ddp-open-states`, `openstates-core`, and
`openstates-scrapers` fresh at build time (all defaulting to `main`), so v22 carries OPEN-293's
fix *and* the full `ddp-open-states`-side backlog the earlier ECR-staleness note flagged (21
commits as of that check, likely a couple more by now) -- worth knowing before assuming this is
an isolated, single-purpose change.

**Registered task-definition revision 26**, image `ddp-scrapers:v22`, otherwise identical to the
current live revision 25 (`v21`). Per the runbook, registering is additive/inert -- nothing
currently running is disturbed, and revision 25 stays live untouched until something explicitly
launches a task against 26. **Not pointing anything live at this myself** -- flagging so you (or
whatever process decides this) can choose when to actually run against revision 26, per the
runbook's own guidance to say "here's the new tag/revision, please run it" rather than build
anything further.
