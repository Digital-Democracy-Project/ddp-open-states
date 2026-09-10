# us clean too -- all four jurisdictions confirmed, thread closed out for real

*Addendum to `notes/rev23-clean-pass-glacier-ir-confirmed-20260910.md`.* `us` retry finished
clean, same as `az`/`mi`/`ma`:

```
us: fetched=574 archived=574 s3_verified=574 s3_unverified=0 persist_errors=0 duration_s=1284
```

All four jurisdictions run against task-definition revision 23 now show `persist_errors=0` and
`s3_verified` exactly matching `archived` with zero `s3_unverified` -- no exceptions, no
partial results. Combined with the direct `GLACIER_IR` confirmation on a real object
(`notes/rev23-clean-pass-glacier-ir-confirmed-20260910.md`), this closes out OPEN-192's Fargate
archive validation end to end: credential rotation handling (OPEN-260), RDS network access
(ingress + egress SG rules), container filesystem permissions (OPEN-263's Dockerfile fix, now on
`main` via #228), and the summary-line/skip-check visibility gap (OPEN-263's code fix) are all
confirmed working together on real production data across all four batch jurisdictions, not
just a single-jurisdiction happy path.

Two threads intentionally still open, tracked separately, not blocking this close-out:
OPEN-266's `is_error=True` rows (35, no existing retry mechanism, needs its own disposition) and
whatever's still pending on OPEN-231/NC. Everything specific to "does the Fargate archive path
actually work end to end" is done.
