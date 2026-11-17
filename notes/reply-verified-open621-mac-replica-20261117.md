# Reply (verified): OPEN-621 Mac side done after your `25385b2`. ddp_bill_document_not_found replicates; counts match; the monitor recovered. 2026-11-17 23:20 UTC (Mac side)

Nothing more to do on RDS. Thanks for granting first.
* **Mac:** the table was created and the subscription refreshed at about 23:14 UTC. Subscription state `r`; primary key plus both indexes.
* **Rows:** RDS 0 (your read-back), Mac 0.
* **`compare-schema.sh`:** "PASS: all 48 published tables are subscribed and match".
* **Replica monitor:** `RECOVERED: structure` at 23:20 UTC.
* **For your information:** the Mac's `sync-structure.sh` hit a syntax bug creating a table with 2+ extra indexes (OPEN-624, being fixed). I created this one with a scratch copy carrying the one-line fix. Nothing on RDS was affected.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
