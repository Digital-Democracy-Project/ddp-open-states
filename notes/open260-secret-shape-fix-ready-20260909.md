# OPEN-260: secret-shape fix is up, here's what to set once it's merged

*Replies to `notes/open260-secret-shape-bug-found-20260909.md`.* Real bug, fixed. Two PRs:

- `ddp-sync` [#128](https://github.com/Digital-Democracy-Project/ddp-sync/pull/128)
- `openstates-core` [#44](https://github.com/Digital-Democracy-Project/openstates-core/pull/44)

`resolve_rds_database_url()` no longer reads `host`/`port`/`dbname` from the secret at all --
only `username`/`password` still come from there. The other three now come from their own env
vars, checked up front (fails before ever calling Secrets Manager if any are missing).

## Once #128 merges, please set on the `ddp-sync` host

You already have all three real values from setting this up the first time:

```
RDS_HOST=ddp-openstates.cvxdhm1ogxug.us-east-1.rds.amazonaws.com
RDS_PORT=5432
RDS_DBNAME=openstates
```

Same place `RDS_CREDENTIALS_SECRET_ARN` already lives (`render-env.sh`'s generated `.env`).
Restart `ddp-sync` again so it picks them up, same as before.

Then re-run the same direct-connection test from `notes/confirmed-stale-credential-not-fargate-plumbing-20260909.md`
to confirm the fixed version actually resolves and connects end to end -- that's still the one
thing standing between this and closing out OPEN-260's "verify against a real rotation"
criterion, and then finally re-running the OPEN-192 Fargate archive validation that's been
blocked on this the whole time.
