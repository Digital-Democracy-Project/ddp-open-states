# OPEN-290: EC2 side deployed and verified -- ready to close

Pulled PR #152+#153 (`f8524f0`), added the three dispatch-shape env vars to this host's
`docker-compose.prod.yml` matching the Mac's real values (9 artifact types, limit 10000,
include_concept_statements true) -- deliberately left
`LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED` untouched (still `false`, per the standing
decision that flipping it is Ramon's separate, deliberate call).

Rebuilt, no in-flight Fargate tasks at the time, clean restart -- no errors, scheduler back
up with 16 jobs. Verified directly in the running container:

```
artifact_types: ['bill_summary', 'bill_pros_cons', 'bill_vote_yes_frame', 'bill_vote_no_frame',
  'bill_supporting_orgs', 'bill_opposing_orgs', 'bill_impact_analysis', 'bill_topics',
  'bill_changelog']
limit: 10000
include_concept_statements: True
enabled (still correctly False): False
```

Also confirmed at the code level (not just config): `_trigger_legbot_session_via_mac_wireguard`
now builds its URL against `/ddp-sync/v1/trigger/bill-artifact-generation` (the consolidated
endpoint), and `/trigger/scraper-session-legbot` no longer exists as a registered route on this
host's image (only historical comments referencing the old name remain).

Have not fired a real end-to-end test of the new consolidated path yet (didn't want to do that
without checking in first, given the flag stays off and any real test needs the same
in-memory-override approach as before). Let me know if you'd like that run, or if this
verification is sufficient to close OPEN-290 as-is.
