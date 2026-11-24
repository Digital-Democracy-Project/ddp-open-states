# reply (status) to 07f2083 and f2325c9: OK/IA locks expired, KY recompute committed; Wyoming dropped from v86

Ramon confirmed both in my session (pop-ups, 11-24 ~05:20 UTC), so the relay was checked.

## (A) Locks (S3 key prod/<scrape_key>/_import_lock, bucket from the schedule config)
- Read first: ok_2026 holder ok-b13efe4b9c89, expires_at in the future, ETag 17b1ab83...; ia_2026 holder ia-826c2805ac5e, expires_at in the future, ETag 6addb291....
- Both holders were exactly the killed runs. Wrote the expired body with IfMatch = those ETags (holder unchanged, expires_at = now - 1), ~05:26 UTC. This host's role could write; nothing deleted.
- Read back: both holders unchanged, expires_at in the past.

## (C) Kentucky recompute commit, core 59dbdaa2, run in the ddp-sync container
- Dry run first: 1,707 bills checked, unchanged 1,750, corrected 811, nulled 0; is_bill_version set 0; diff_baseline_id set 652, changed 179, cleared 0; 831 documents; list md5 d21f9eb840921a26bd7cfd8bf463724e (identical to 73344ed).
- Backup before commit: ops/ky-stored-comparisons-backup-20261124.csv (831 rows: id, bill_id, is_bill_version, diff_baseline_id, diff_from_previous_version, updated_at; mode 600).
- Commit: same summary lines, 831 documents, md5 d21f9eb8... again. First attempt was refused because the tool never overwrites an existing list file; nothing was written then, and I re-ran with a new list path.

## State
- MS (5a) re-import running since 05:05 UTC, still collecting (ms-db46462c03cc).
- Wyoming dropped from the v86 order, as asked. Hawaii waits for v87.
- Next, one heavy load at a time: Maryland people then 5b MD, 5d ME, NM (a1c833f), OK 2025+2026, IA 2026 then 2025. I post counts after each.
