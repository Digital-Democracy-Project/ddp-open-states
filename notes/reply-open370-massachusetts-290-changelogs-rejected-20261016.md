# Reply: OPEN-370 DONE, the 290 Massachusetts changelogs are rejected (nothing deleted). (prod agent, EC2 host, 2026-10-16 ~01:21 UTC)

Followed GO note `1ecd578c`. Ramon confirmed the go in this session. Only `review_status` changed, on exactly the 290 rows of your set.

## Gates and steps
1. **Quiet:** 0 Mac writes (artifacts/versions/ensure/concept-statements) in the 5 minutes before.
2. **Set (read-only):** your query returned **290** rows, all `status=complete`, `review_status=approved`. All Massachusetts changelogs are in it (290 of 290; Massachusetts has 77,846 artifacts of all types).
3. **Backup:** `/home/bitnami/ops/ma-changelog-reject-backup-20261016.csv` on this host, mode 600, **290 rows** plus header, sha256 prefix `2e6a85dc18bde13b`. Columns: `artifact_id, status, review_status, reviewed_at, reviewed_by_id, failure_stage, failure_reason, validated_at, validation_notes, pinecone_synced_at, chunk_count` (review fields only; no text).
4. **One-row test:** row **238787** (bill S3031, session 194th, bill_version 38607) rejected with the model's `.save()`. Read back: DB `review_status=rejected, status=complete`; `GET /api/bill-artifacts/status/?jurisdiction=ma&session=194th&gov_id=S3031&versions=all` (service token, public host header) returned for version 38607 `Chapter Law Text (Enacted)`: `{'status': 'complete', 'review_status': 'rejected', 'compare_version_id': 38609}`. The other 289 rows were still approved (289 / 1).
5. **The rest:** 289 rows rejected, one `.save()` each, no error.

## Verification (read-only)
* The set now: **290 rejected, 0 approved.** All Massachusetts changelogs: 290 (no others exist).
* Total `common_billartifact` rows: **341,637 before and after.**
* `ddp_bill_version_document` for Massachusetts on RDS, before and after: **12,014 documents, 332 Chapter Law Text, 291 with a diff (all 291 on Chapter Law Text), 7,998,573 diff characters** in both counts. Untouched.
* Public read `GET /api/bill-artifacts/current/` for S3031: `{"found":false}` (the row left the public read). `/api/status/` 200. No non-scanner ERROR in the web log.

## Notes
* My first attempt to read the status endpoint from inside the container returned 400 (local host name not accepted); with the public host header it worked. No effect on data.
* Nothing else touched: no Massachusetts scrape, archive, recompute or LegBot run, no diff or document changed, no flag or schedule change. Restoring from the backup is Ramon's and your decision.
* Commands: scripts run through `python manage.py shell` in `ddp-broker-py-web-1`; database address not used or printed.
