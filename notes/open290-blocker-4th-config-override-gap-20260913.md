# OPEN-290: blocker found before merge -- 4th instance of the SYNC-51/OPEN-193 config-override gap

Checked what you asked (EC2's `artifact_types`/`limit`/`include_concept_statements`) --
found the "unset artifact_types" concern is real, but the actual root cause is worse than
just missing an env var:

```
artifact_types: []
limit: 10000
include_concept_statements: True
```

`limit`/`include_concept_statements` happen to match the Mac's values only because they're
each field's own dataclass default, not because anything set them. `artifact_types` has no
safe default (empty list), which is why it's the one that's actually broken.

**Real root cause, confirmed in code**: all three
(`legbot_scrape_completion_trigger_artifact_types`/`_limit`/
`_include_concept_statements`) are only ever read inside `_load_from_env()`
(config.py:696-709) -- which never runs on this host, since Secrets Manager succeeds here
and short-circuits it entirely. This is the exact same bug class as `REDIS_URL` (OPEN-193)
and `mac_ddp_sync_base_url`/`rds_openstates_api_base` (found and fixed earlier today, PR
#149) -- a 4th instance, just not yet hit because nothing needed these three fields to
resolve host-locally until OPEN-290's own design change. Setting
`LEGBOT_SCRAPE_COMPLETION_TRIGGER_ARTIFACT_TYPES` etc. as a plain compose environment
variable on this host would have **zero effect**, silently -- confirmed directly against the
code, not assumed.

**Before merging OPEN-290**: these three fields need the same per-host override treatment
`REDIS_URL`/`mac_ddp_sync_base_url`/`rds_openstates_api_base` already have in
`get_settings()` (the `env_redis_url`-style loop, config.py ~757-778). Once that's in place,
I'll set the matching env vars in this host's `docker-compose.prod.yml` (the same 9 types +
limit + include_concept_statements the Mac uses) and verify they actually resolve before you
merge/deploy.

Flagging this now specifically so OPEN-290 doesn't ship with the exact silent-400 failure
mode you were already worried about, just from an extra cause underneath the one you named.
