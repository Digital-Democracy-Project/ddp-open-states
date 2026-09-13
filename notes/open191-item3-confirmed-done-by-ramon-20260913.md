# OPEN-191: item 3 (the actual cutover) is confirmed done -- Ramon directly

Update to `notes/open191-real-status-check-20260913.md`: drop item 3 from what you're
checking. Ramon confirmed directly: **the live broker traffic is already cut over** -- it's
not hitting the old on-prem path anymore, it's pointed at RDS/the new api-v3 for real
production requests.

If you have easy access to the real technical evidence for this (which config/deploy change,
when, any confirmation logs) that would be good to have on record on the ticket, but don't go
out of your way for it -- Ramon's own confirmation is authoritative here, not something that
needs independent re-verification.

Still real, still open, still worth checking for real:

1. **Tier 1 + Tier 2 quality checks against RDS** -- never run as of the ticket's last update
   (2026-09-01), Ramon's own explicit hold on the cutover. Has this actually been run since?
   If not, can you run it now and report real coverage/pass numbers?
2. **Freshness AC** -- does today's OPEN-193/AC6 measurement (7 of 8 measured `cloud_path`
   jurisdictions pass the same ≤24h/≤7-day bar this ticket uses) satisfy this ticket's own
   freshness AC, or does it need its own separate check against whatever data source the
   broker's real cutover traffic actually reads from now?
