# Full detail on the batch's fetch_errors, plus a bigger finding: silent persist failures

*Follow-up to `notes/all-jurisdictions-batch-results-20260909.md`.* Dug into every
`fetch_errors` instance and the exact crash cause for `us`, reading the code path
(`archive_bill_versions()`, `openstates-core/openstates/cli/text_extract.py`) alongside the raw
logs rather than just the counts.

## `fetch_errors` (va=2, mi=15, ma=20): all genuine 404s, not a bug

`fetch_errors` increments at one specific point (`text_extract.py:1587-1589`): a generic
`except Exception` around the actual HTTP fetch, logged as `failed to fetch {url}: {e}`. Every
single instance across all three jurisdictions is a plain `404 while retrieving <url>` --
source documents that no longer exist at the URL our stored bill version links point to
(examples: `lis.blob.core.windows.net/files/1222762.PDF` for VA, several
`legislature.mi.gov/Home/GetObject?objectName=...` redirects for MI, several
`malegislature.gov/Bills/194/HD*.pdf` for MA). Not a code bug -- this is what a genuinely stale
source link looks like. Might be worth a separate look at whether these specific bill versions'
stored URLs need refreshing, but that's a data-quality question, not an archiver bug.

## Bigger finding: local persist failures are completely invisible in the summary counts

Every jurisdiction with real fetch activity (`az`: 32, `mi`: 12, `ma`: 74, `us`: 68) hit
`[Errno 13] Permission denied: '/app/_archive'` on **every single fetched document**, with zero
exceptions. Traced the code: `counters["fetched"] += 1` happens *before* the local write attempt
(`text_extract.py:1600`), and the write's `except OSError` (`:1610-1612`) just logs
`"failed to persist {url} to {path}: {e}"` and `continue`s -- **no counter increments at all**,
not `fetch_errors`, not a new one. So `fetched=74` for `ma` looks like real progress in the
summary line, but every one of those 74 downloads was immediately discarded -- none reached the
`_upload_and_verify()` S3 step, which is exactly why `archived`/`s3_verified`/`s3_unverified`
are all zero everywhere in today's entire batch, dry-runs included. **This isn't "nothing new to
archive" -- it's "everything new to archive is silently failing at the local-write step," and
the summary line's own shape can't tell you that.**

Sample lines (identical shape across all four jurisdictions, only the URL/path differ):
```
failed to persist https://legislature.mi.gov/documents/.../House_Introduced_Bill-....pdf to
/app/_archive/bills/raw/mi/2025-2026/lower/HB6324--.../House_Introduced_Bill-....pdf:
[Errno 13] Permission denied: '/app/_archive'
```

Worth two things: (1) a real fix to whatever's blocking writes to `/app/_archive` in the task
definition (`readonlyRootFilesystem`/`mountPoints`, per the earlier note -- still can't confirm
directly, `ecs:DescribeTaskDefinition` denied on this host's role), and (2) separately,
`archive_bill_versions()` arguably should count local-persist failures somewhere distinct from
"fetched" so a clean-looking summary can't mask a systemic write failure like this one.

## `us`'s actual crash: not the persist issue, a dropped DB connection

The 68 persist failures in `us`'s log were non-fatal (same silent-continue as everywhere else).
The real fatal traceback, ~14 minutes into the run:

```
File ".../text_extract.py", line 1497, in archive_bill_versions
    jurisdiction_name = bill.legislative_session.jurisdiction.name
...
django.db.utils.OperationalError: server closed the connection unexpectedly
```

A lazy-loaded Django FK access (`bill.legislative_session.jurisdiction`) triggered a fresh query
against a connection RDS had already closed server-side, after the run had been alive and
iterating for several minutes. Looks like a connection-lifetime/idle-timeout issue on a single
long-lived DB connection held across a long per-bill loop with HTTP fetches interspersed --
worth checking Django's `CONN_MAX_AGE` / whether connection health is verified before reuse
mid-loop, separately from the persist-permission bug above. Not something to fix from here.
