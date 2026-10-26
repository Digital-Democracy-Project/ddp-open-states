# CORRECTION to two of my replies of 2026-10-26: ddp-sync on the EC2-broker host now loads its settings from **Secrets Manager**, not only from the rendered `.env`; I had checked only environment variables

The operator asked whether ddp-sync reads `CAMS_API_TOKEN` from Secrets Manager. It was a fair question: **I had checked only `.env` files and container environment variables, and the app reports `config_source: secrets_manager`** (read now through `/ddp-sync/v1/health`; my read on 2026-10-19 said `env`; the container was restarted 10-22 21:45 UTC with the 16-commit deploy; I do not know which change flipped it). So env-var checks do not show what the app is actually using. I re-checked against the app's **loaded settings** (printing only yes/no, lengths and non-secret lists) and the secret's key **names** (no values).

## 1. INFRA-12 (`reply-infra12-cams-reachability-20261026.md`): the conclusion stands, the reasoning was incomplete
* **The running app's loaded settings have no CAMS token:** `settings.cams_api_token` is **not set (length 0)**, and `cams_base_url` is still the default `http://localhost:8000` (not the Mac). So the "no token on this host" answer is **true for the app too**, not just for the environment.
* **The secret `ddp-sync/credentials` has 36 keys and none contains "cams" or "codebot"** (it does hold `mac_ddp_sync_api_key`, `rds_openstates_api_key`, `slack_bot_token`, the Webflow, OpenAI and Pinecone keys, `ddp_openstates_jurisdictions` and others). So `render-env.sh` not mapping CAMS is not hiding a CAMS value in the secret.
* **How LegBot pipelines are started from this host does not use `CAMS_API_TOKEN`:** the archive hook and the manual trigger call the **Mac's ddp-sync** (`/ddp-sync/v1/trigger/bill-artifact-generation`) with `mac_ddp_sync_api_key` (set), and the Mac's own ddp-sync/CAMS does the inference. The only direct-to-CAMS code in this host's ddp-sync that I found is the failure report in `openstates_archive.py` (reads `os.getenv("CAMS_API_TOKEN")`, skipped when empty) and the ScrapeBot client (`settings.cams_api_token`); both are inactive here for lack of a token.
* One more wording fix: my reply said the token "is absent, not blank" for `.env` and containers; for the app's settings it is **empty** (not set).

## 2. OPEN-330 (`reply-open330-live-jurisdiction-env-values-20261022.md`): item 2 was wrong in substance
I reported `DDP_OPENSTATES_JURISDICTIONS` and `LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST` as **unset** on ddp-sync because they are not in `.env` or the container env. With `config_source: secrets_manager` the **effective** values (read from the app's loaded settings just now) are:
* **`ddp_openstates_jurisdictions` = `['FL','WA','US','VA','MI','MA','UT','AZ','NC']`** (it comes from the `ddp_openstates_jurisdictions` key in the `ddp-sync/credentials` secret). That differs from the broker's list (`MI,UT,US,VA,AZ,WA,FL,NC`: no MA here, MA in ddp-sync). `bill_sync_enabled` and `legislator_sync_enabled` are both false on this host, so the pipelines that read it are off here, as I said; but a drift check comparing "this host's live list" should use the effective list above, not the env var.
* **`legbot_rds_replica_jurisdiction_allowlist` = `[]`** (empty; not in the secret either).
I do not know when the effective list last changed, or whether the secret's list is shared by the other ddp-sync hosts (the secret is the shared `ddp-sync/credentials` blob). My note of 10-21 asking whether `render-env.sh`/the rendered `.env` is still needed also needs updating: on this host the app already prefers Secrets Manager.

## Not changed / not checked
Nothing was changed. I read the secret's key names (no values) and the app's loaded settings (yes/no and non-secret lists only). Not checked: the other ddp-sync hosts' config source; which commit flipped `config_source`.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
