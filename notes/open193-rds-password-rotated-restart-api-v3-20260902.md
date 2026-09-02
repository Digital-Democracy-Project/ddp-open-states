# OPEN-193/OPEN-191 — RDS master password rotated; api-v3 needs a restart now, not later

*Replies to the exposed-credential flag in `notes/open193-canary-blocked-deploy-question-20260902.md`.*

Ramon rotated the RDS master password just now, closing out that open item.

**Time-sensitive, please action first**: `api-v3`'s container on this host has the old password
baked into its environment (`DATABASE_URL`, from container start -- the same value your
`docker inspect` check surfaced). It is not re-fetching the secret live. Now that rotation has
happened, that container is running on an invalidated credential -- any *new* database
connection it opens will fail; already-open pooled connections may keep working briefly but
won't survive being recycled. **Restart the `api-v3` container** so it re-reads the current
secret and reconnects cleanly. Please do this ahead of (or as part of) the systemd-wrapper work
already queued for it -- don't wait for that packaging to land first, since this is a live
break, not a design improvement.

Once restarted, worth a quick confirmation the same way the RDS connection was verified
earlier on this thread: a real query against `ddp-openstates` succeeding, not just the process
being up.

Everything else queued (`ddp-sync` Docker packaging, the api-v3 systemd wrapper itself, the
Redis DB-separation check) stands as already described.
