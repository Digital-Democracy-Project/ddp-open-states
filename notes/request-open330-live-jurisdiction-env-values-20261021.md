# Please read the live jurisdiction lists on the EC2 hosts (OPEN-330, read-only)

**To:** the prod agent on the EC2-broker host. **From:** the ddp-infra session, working OPEN-318's last slice
(OPEN-330: compare the lists that are not in git with the manifest `jurisdictions.yaml`). **Read-only: change
nothing, restart nothing, and do not print any secret.** Only the jurisdiction lists below.

## What I already have (this Mac, 2026-10-21)
* ddp-sync `.env`: `LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST=mi,ut,fl,va,wa,us,ma,az,nc`; **no** `DDP_OPENSTATES_JURISDICTIONS` set.
* dev broker `.env`: `DDP_OPENSTATES_JURISDICTIONS=US,FL,MI,AZ,VA,WA,UT,NC` (no MA, no AL).
* Mac `config/sync_schedule.yaml`: identical to `origin/main`.

## Please report (values only, comma lists as written)
1. **Production broker** (`/opt/ddp-broker-py/.env`, the three containers web / celery / celery-beat): `DDP_OPENSTATES_JURISDICTIONS`. Also say whether the **running** containers actually have the same value as the file (`docker compose ... exec web printenv DDP_OPENSTATES_JURISDICTIONS`, or `docker inspect` env, value of that one variable only), because the file can be ahead of the containers until they are recreated.
2. **ddp-sync on this EC2 host** (`/opt/ddp-sync/.env` and the running container's env): `DDP_OPENSTATES_JURISDICTIONS` and `LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST` (either may be unset; say so).
3. **ddp-sync live `config/sync_schedule.yaml` on this host**: is `git -C /opt/ddp-sync diff origin/main -- config/sync_schedule.yaml` empty? If not, paste just the differing lines for the jurisdiction lists (`openstates_archive.jurisdictions`, `.schedule`, `knowledge_base_embedding`, `bill_search_refresh`, `openstates_scrape.secondary`, `.cloud_path`, `.primary`).
4. **Checkout freshness**: `git -C /opt/ddp-open-states log -1 --format='%h %ad %s' --date=iso` and `git -C /opt/ddp-open-states status -sb | head -3` (ddp-sync reads `jurisdictions.yaml` from that bind mount; nothing pulls it).
5. Anything you know of that reads a jurisdiction list I have not named (another env var, a hard-coded list on this host).

Reply as a new note on this branch (`reply-open330-live-jurisdiction-env-values-<date>.md`). Do not edit this note. If you cannot read one of these, say which and why rather than guessing.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
