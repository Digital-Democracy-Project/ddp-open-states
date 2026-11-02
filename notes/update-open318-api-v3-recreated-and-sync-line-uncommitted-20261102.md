# Update to OPEN-318: api-v3 recreated and now serves the new manifest; one ddp-sync line is still uncommitted, 2026-11-02 02:10 UTC

**api-v3 (this host):** I recreated only the `api` service of the `ddp-openstates-rds` project (`up -d --no-deps --no-build --force-recreate api`) at 02:10:36 UTC, because the single-file mount kept the old `jurisdictions.yaml` after the 01:32 pull (the compose file's own caveat). The old container log is saved (`api-v3-pre-manifest-refresh-20261102T0210Z.gz`). Same image `145414bb6b51`, Redis not restarted, healthy within 16 seconds, down about that long.

**Checked afterwards:** the file in the container and on the host have the same md5. The broker's own client fetched `/ddp/enrollment` fresh and got `mtime 2026-11-02T01:32:44.330038+00:00` (the host file's mtime) and **10 jurisdictions**. The broker's routed list is unchanged: **AZ FL MI NC US UT VA WA**. 0 nginx 5xx in the next 8 minutes. (The endpoint answers 403 without the key; I did not print or use the key by hand.)

**Still owed by dev:** `/opt/ddp-sync/infrastructure/docker-compose.prod.yml` on this host has one uncommitted edit (3 comment lines and `- JURISDICTION_MANIFEST_MODE=authoritative`). Please commit the same lines to main. A later pull that touches that file will refuse until I run `git checkout -- infrastructure/docker-compose.prod.yml`, so tell me before you merge anything that changes it.

**Correction:** in my earlier reply (`62e924aa22`) I described the ddp-sync edit in a garbled phrase; the true diff is those 3 comment lines plus the 1 setting line.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
