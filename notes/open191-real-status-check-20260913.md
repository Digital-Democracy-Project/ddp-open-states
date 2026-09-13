# OPEN-191 (Phase 2): real current status check

Ramon asked whether this is actually done, given how much has landed today. Jira still shows
**In Progress**, and the ticket's own text is explicit about being blocked on OPEN-193 plus one
specific item that (as of the ticket's last update, 2026-09-01) had never been run. Rather than
trust that text at face value (it may be stale the same way OPEN-192/193 were), can you check
each of these directly against the real system, same standard as the other phase checks today?

1. **Tier 1 + Tier 2 quality checks against RDS** (`quality_check.py --coverage` / `--tier2`,
   via `DATABASE_URL_OVERRIDE` pointed at RDS). Ramon's own explicit hold: "I'm going to hold
   the switchover until I'm completely confident... run the tier 1 + tier 2 quality checks
   against RDS before we cutover." Ticket says not yet run as of 2026-09-01. Has this actually
   been run since, by anyone, for real? If not, can you run it now and report the real
   coverage/pass numbers (thresholds: Tier 1 identifier coverage >=95% per jurisdiction/session,
   Tier 2 >=95% pass on a 250-bill `--tier2-random` sample)?

2. **Freshness within the agreed window.** The ticket says this was reopened pending OPEN-193
   shipping a real feed and freshness being re-measured. That re-measurement already happened
   today for OPEN-193/AC6 (7 of 8 measured `cloud_path` jurisdictions pass OPEN-191's own
   ≤24h/≤7-day bar; MA fails, tracked as OPEN-283). Does that same measurement satisfy this
   ticket's own freshness AC, or does this ticket need its own separate check (e.g. against a
   different jurisdiction set, or the broker's actual current data source rather than
   `cloud_path`'s)?

3. **The actual cutover itself** -- is `ddp-next`/the broker still hitting the old on-prem path
   for real requests, or has anything already repointed it to RDS/the new api-v3 permanently?
   (Distinct from OPEN-272's earlier work, which repointed the Mac's own api-v3 at the RDS
   replica -- this AC is about the production broker's real live traffic path.)

Report the real state of each, however it comes out -- if all three are genuinely still open,
that's a real answer too, just want it checked rather than assumed from a doc that may be
stale.
