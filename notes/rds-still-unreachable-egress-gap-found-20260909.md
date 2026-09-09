# Inbound rule confirmed live, but same timeout again -- the real gap is egress, not ingress

*Replies to `notes/rds-sg-rule-added-rerun-step3-20260909.md`.* Confirmed the new inbound rule
first: `sg-08ece6ced1406e4a8`'s `IpPermissions` now includes TCP 5432 from `sg-09346518873d48a08`
("Rule to allow connections from Fargate instances with sg-09346518873d48a08 attached") —
present and correct.

Re-ran the exact same validation anyway (new RUN_ID `ut-archive-a70cb9cd43fd`, same task-def
`ddp-scrapers:19`, same `ut`/`cloud_archiver.py`). **Identical failure** — same
`psycopg2.OperationalError: ... port 5432 failed: Connection timed out`, same 130-second timeout,
same clean error handling and completion record on the app side.

## Real root cause this time

Checked `sg-09346518873d48a08`'s own **egress** rules (hadn't checked these before — only
checked its inbound, which is correctly empty since nothing calls *into* a scraper task).
`IpPermissionsEgress` allows outbound TCP **80 and 443 only** — nothing for 5432. The Fargate
task's own security group never had permission to *send* traffic to Postgres at all. The RDS-side
inbound fix was real and necessary, just not sufficient — this task was never allowed to leave
its own security group on that port in the first place, regardless of what RDS accepts. Same
underlying story as the ingress gap: `sg-09346518873d48a08` was scoped for HTTP/HTTPS scraping
traffic only, since no prior Fargate task ever needed a direct DB connection.

## Next step

Needs an egress rule added to `sg-09346518873d48a08` allowing outbound TCP 5432 (destination
`sg-08ece6ced1406e4a8` or the RDS instance's CIDR, whichever's more natural to author). Not doing
this myself — same category as the ingress rule, a production network-access change. Once it's
added, I'll re-run the validation again with a fresh RUN_ID — no changes needed on the
image/task-def side, this has been purely a networking question both times.
