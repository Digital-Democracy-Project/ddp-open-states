# GO: OPEN-370, hide Massachusetts's 290 whole-document changelogs on the production broker. Reject, never delete. (dev side, 2026-10-15 EDT / 2026-10-16 UTC)

**STATUS: GO, with gates.** Ramon decided this in the Mac session (2026-10-15): keep all stored data, hide the 290 Massachusetts change summaries from the public site, and have the production agent do it. A failed gate is not permission to improvise: stop and report. If a HOLD note from Ramon appears on this branch, follow it instead. This is independent of the OPEN-352 go-live note and does not wait for it.

Jira: **OPEN-370**.

## 1. Why

Massachusetts gives every new version a new bill number, so versions cannot be linked by number. Its only comparison is a PDF (`Bill Text`) against an HTML page (`Chapter Law Text (Enacted)`), so each of the 290 changelogs is built on a single whole-document diff and describes the whole bill as rewritten. The 297 `Chapter Law Text (Enacted)` documents, their links to the earlier bill numbers and the stored diffs are the **only** evidence of which bill numbers became the final law, so **nothing is deleted, no document is touched, and no diff is nulled** (no `recompute-diff-order` for Massachusetts).

## 2. Exactly what to change

Only `review_status`, only on these rows (production, read-only trial run by Ramon on 2026-10-15 returned exactly 290, all `status = complete`, `review_status = approved`):

```sql
-- the set (read-only; expect 290 rows)
SELECT a.id, a.status, a.review_status
FROM common_billartifact a
JOIN common_billversion v ON v.id = a.bill_version_id
JOIN common_billversion c ON c.id = a.compare_version_id
WHERE a.artifact_type = 'bill_changelog'
  AND lower(v.jurisdiction) IN ('ma', 'massachusetts')
  AND v.version_note ILIKE 'chapter law text%'
  AND c.version_note = 'Bill Text';
```

Production has 290 live Massachusetts changelogs in total and all 290 are this pair, so no other Massachusetts row may be touched.

## 3. How (the same "reject, never delete" step the Utah set used)

1. **Backup first:** save, to a file on the host, for every one of the 290 rows: `id`, `review_status`, and every other review field the model carries (reviewer, review time, notes, `validation_notes`), so the exact prior state can be restored. Report the file path and the row count (must be 290).
2. **One-row test:** reject **one** row through the model's `.save()` (not a queryset `.update()`, as for Utah, so any `save` side effects run). Read it back through the broker's status endpoint (`/api/bill-artifacts/status/...`, the same read ddp-sync uses): it must show `review_status: rejected`, and the other Massachusetts rows must be unchanged. If anything looks wrong, restore that one row from the backup and stop.
3. **The rest:** reject the remaining 289, one `.save()` per row.
4. **Verify (read-only):** the set above now returns **290 rows with `review_status = rejected`**, none approved; all other Massachusetts rows: there are none; total `common_billartifact` rows unchanged; `ddp_bill_version_document` rows for Massachusetts untouched (read-only count before and after: Chapter Law Text documents and their stored diffs).
5. If a count differs, a `.save()` errors, or it stops partway: **stop and report**. Do not retry and do not roll back without authorization; paste the output. Restoring from the backup is for Ramon and me to decide.

Do it in a quiet moment (no Massachusetts generation is expected: ddp-sync skips cross-media pairs, SYNC-110). Do not run a Massachusetts scrape, archive, recompute or LegBot run.

## 4. Reply

A `reply-open370-...` note: the backup file path and row count, the one-row test and its read-back, the final verification counts, the times, and the exact commands (database address masked).

## 5. Not authorized

Any delete; any change to `ddp_bill_version_document` or any Massachusetts diff; a Massachusetts `recompute-diff-order`; any other jurisdiction or artifact type; a flag or schedule change; restoring or rolling back without authorization.
