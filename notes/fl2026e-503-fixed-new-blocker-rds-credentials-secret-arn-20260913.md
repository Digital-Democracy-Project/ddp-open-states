# FL 2026E test: 503 fixed, real request reached the Mac, but ALL 22 bills failed the same way -- new config gap

Broker config fix confirmed working: no more 503. Switched from time-window auto-discovery to
directly dispatching the known session (`_trigger_legbot_session_via_mac_wireguard('FL',
'2026E', ...)`, same real function, just skipping the auto-discovery step since a 60-day
lookback couldn't isolate 2026E alone from the other FL sessions touched in the same
overlapping window -- see the prior note on that).

**Real result, correctly scoped**: `bills_considered: 22, bills_processed: 22` -- exactly our
22 bills, nothing broader. But every single one failed identically:

```
error: replica_not_fresh: rds_credential_unavailable: RDS_CREDENTIALS_SECRET_ARN not set --
refusing to guess which secret to read
```

This is the OPEN-275/276 replica-freshness check -- confirmed enabled on the Mac (per your
earlier note, both the flag and the 6-jurisdiction allowlist including FL are live there). It's
running as designed, but can't actually complete: it needs to know which Secrets Manager ARN
holds the RDS credential to check freshness against, and that isn't configured on the Mac
(`RDS_CREDENTIALS_SECRET_ARN` env var not set there, presumably). Fails closed rather than
guessing or skipping -- correct, safe behavior, just blocking every bill.

Clean failure again -- nothing generated, nothing written, no data touched. Full raw result
available if useful (22 identical per-bill error entries).

Could you check what `RDS_CREDENTIALS_SECRET_ARN` should be set to on the Mac for this check
to actually run? (This EC2 host's own `render-env.sh` writes the same-named var from the RDS
secret's own ARN for a different purpose -- OPEN-260 -- might be the same value needed here,
but that's a guess on my part, not confirmed for the Mac's own freshness-check code path.)

Not retrying again until this is resolved.
