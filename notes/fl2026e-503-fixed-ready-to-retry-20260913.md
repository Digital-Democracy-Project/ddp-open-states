# FL 2026E test: 503 fixed, ready to retry

Ramon uncommented `ONDEMAND_BROKER_API_BASE_PROD`/`ONDEMAND_BROKER_API_TOKEN_PROD` (and
the adjacent `DDP_BROKER_API_BASE`/`DDP_BROKER_API_TOKEN`, also previously commented) and
kickstarted `ddp-sync`. Confirmed directly in the new running process (PID 34391,
started 16:23:31 local): both `ONDEMAND_BROKER_API_BASE_PROD` and
`ONDEMAND_BROKER_API_TOKEN_PROD` are live, matching
`https://api.digitaldemocracyproject.org/broker` and the expected token. Health check
green.

Ready for your retry -- and per your own earlier note, worth narrowing the lookback
window first so it only resolves 2026E (not F/D/plain-2026 too), to keep this to the
agreed 22-bill scope.
