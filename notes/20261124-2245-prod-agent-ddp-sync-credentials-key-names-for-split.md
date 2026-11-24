# ANSWER for Ramon's request: the full list of key names in `ddp-sync/credentials` (names and value types only, NO values) so you can plan how to split it

Read at 11-24 ~23:00 UTC with ddp-sync's own AWS role from this host (read only; nothing printed or stored but names and JSON types). The secret has **39 keys**. Real credentials vs plain settings below are **my reading of the names**, not verified against the values.

## All 39 key names (name, JSON type)
```
_comment  str
api_key  str
blacklist  list
brevo_api_key  str
brevo_rate_limit_rph  int
codebot_slack_icon_emoji  str
congress_api_key  str
ddp_openstates_jurisdictions  list
mac_ddp_sync_api_key  str
openai_api_key  str
openai_embedding_model  str
openstates_api_key  str
operator_alert_token  str
organizations  list
pinecone_api_key  str
pinecone_environment  str
pinecone_index_name  str
pinecone_namespace  str
rds_openstates_api_base  str
rds_openstates_api_key  str
redis_url  str
slack_bot_token  str
sync_interval_minutes  int
va_api_key  str
votebot_quick_action_buttons  bool
votebot_slack_app_token  str
votebot_slack_bot_token  str
votebot_slack_support_channel  str
webflow_api_token  str
webflow_assets_read_write_key  str
webflow_bills_collection_id  str
webflow_categories_collection_id  str
webflow_jurisdiction_collection_id  str
webflow_legislators_collection_id  str
webflow_organizations_collection_id  str
webflow_scheduler_api_key  str
webflow_site_id  str
webflow_votebot_api_key  str
zapier_webhook_url  str
```

## My grouping by name (so you can size the split)
- **Slack / alerting (5):** slack_bot_token, operator_alert_token, codebot_slack_icon_emoji (a setting, not a secret), zapier_webhook_url, brevo_api_key (+ brevo_rate_limit_rph, a setting).
- **Webflow (13):** webflow_api_token, webflow_assets_read_write_key, webflow_scheduler_api_key, webflow_votebot_api_key (4 credentials); webflow_site_id and webflow_{bills,categories,jurisdiction,legislators,organizations}_collection_id (6 ids, settings).
- **Embeddings / vector store (6):** openai_api_key, pinecone_api_key (2 credentials); openai_embedding_model, pinecone_environment, pinecone_index_name, pinecone_namespace (4 settings).
- **api-v3 / OpenStates (3):** rds_openstates_api_key, openstates_api_key (2 credentials); rds_openstates_api_base (a setting).
- **Scraper source keys (2):** congress_api_key, va_api_key (the one Ramon added today). These are what the scraper task definitions carry as plain values.
- **ddp-sync's own (3):** api_key, mac_ddp_sync_api_key, redis_url (credentials; redis_url may hold a password).
- **VoteBot (4):** votebot_slack_app_token, votebot_slack_bot_token (2 credentials); votebot_slack_support_channel, votebot_quick_action_buttons (settings). **Nothing in the ddp-sync repo references any of the four names (case-insensitive grep of /opt/ddp-sync, all files): they look like they belong to another service that reads this secret.**
- **Plain settings and lists, not credentials (7):** `_comment` (a note), blacklist (list), organizations (list), ddp_openstates_jurisdictions (list), sync_interval_minutes (int).
  (Counted overall: about 17 keys look like credentials, the rest are settings or lists.)

## What I could and could not check
- I counted, for each name, which `.py` files under `/opt/ddp-sync/src` mention it (word match): `api_key` 24, `organizations` 22, `webflow_votebot_api_key` 10, `webflow_bills_collection_id` 8, `rds_openstates_api_base` 7, `rds_openstates_api_key` 6, `legislators_collection_id` 6, `zapier_webhook_url` 5, and 1 to 4 for most others. Case-insensitive, `va_api_key` and the four `votebot_*` names appear in **no** file of the ddp-sync repo, the others do. That only says ddp-sync's code mentions them; it does not tell you **which other services read this secret** (VoteBot? the Mac ddp-sync? the broker?). I cannot see other services' configs or their IAM policies from here (this host's role is read-only on Secrets Manager reads and denied ECS describe); that part is yours and Ramon's.
- The secret's resource policy and which roles can `GetSecretValue` on it: not read by me.
- Some of ddp-sync's settings come from elsewhere (the host `.env`, compose environment), not from this secret: e.g. the GitHub token used for builds lives in /opt/ddp-open-states/.env, not here.
