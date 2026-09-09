# Quick check: is Docker available on this host, for a bigger question than the poppler fix

Separate from the poppler-utils install (go ahead on that as approved) — Ramon and I were
discussing the wider point this investigation raised: this host's `/opt/ddp-open-states/.venv`
is now the third separately-maintained copy of the openstates-core toolchain (alongside the root
`Dockerfile`'s scraper image and `ddp-sync`'s own bundled copy), and today's whole detour was
exactly the kind of drift that setup invites. Rather than adding Fargate task orchestration for
an inherently interactive, investigative tool like `refresh-extraction` (which would trade fast
iteration for CloudWatch-log-polling latency), the idea is: keep running it ad hoc on this host,
but from the same already-correct, already-tested scraper image Fargate uses
(`docker run -it <image> os-text-extract ...`, `DATABASE_URL` pointed at RDS), instead of a bare
venv that's its own third thing to drift.

That only works if Docker itself is usable here for ad-hoc interactive runs. Could you check:

1. `docker --version` / `docker ps` — is Docker installed and usable (or does it need `sudo`,
   or is it not present at all)?
2. Can this host authenticate to ECR and pull `ddp-scrapers` (the same image Fargate tasks run)?
   A plain `aws ecr get-login-password ... | docker login ...` + `docker pull` check is enough —
   no need to actually run anything yet.
3. Rough resource check — enough disk/memory on this host to comfortably run that image
   interactively alongside whatever else runs here (ddp-sync, etc.)?

No urgency on this one — informational, to see whether the idea is even viable here before
treating it as a real plan. The poppler-utils install and the RDS re-runs are still the priority.
