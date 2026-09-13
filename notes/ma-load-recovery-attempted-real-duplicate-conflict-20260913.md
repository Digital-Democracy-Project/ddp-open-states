# MA load recovery: attempted with Ramon's go-ahead, hit a real duplicate-data conflict, not resolved

Following up on `notes/ma-2026-09-06-failure-root-cause-20260913.md`. Ran the by-run-id
recovery for real, twice.

**Attempt 1** failed on my own mistake: `cloud_loader.py` reads `DATABASE_URL` (not
`RDS_DATABASE_URL`, which is what this container actually has set) -- os-update tried
`localhost:5432` and got connection refused. Not a real system problem, just a wrong env var
in my invocation.

**Attempt 2**, with `DATABASE_URL` set correctly to the real RDS connection string: got past
connectivity, bills imported without a fatal error (only benign per-item warnings --
`cannot resolve pseudo id to Organization` for various non-legislative bodies referenced in
bill text, `no people returned for spec` -- neither looks new or MA-specific, consistent with
noise this pipeline already tolerates elsewhere), then **failed for real on vote-event import**:

```
openstates.exceptions.DuplicateItemError: attempt to import data that would conflict with data
already in the import: {'identifier': '', 'motion_text': 'Passed to be engrossed',
'motion_classification': ['passage'], 'start_date': '2025-04-09', 'result': 'pass', ...
'dedupe_key': 'https://malegislature.gov/Journal/House/194/2025/RollCalls#29', ...}
(already imported as Passed to be engrossed on H 4005 in Massachusetts 194th Legislature
(2025-2026))
```

Both `obj1`/`obj2` sources point at the same URL
(`https://malegislature.gov/Journal/House/194/2025/RollCalls`), so this looks like the exact
same real-world roll call, recorded twice with something differing enough (dedupe_key
construction, most likely) that the importer treats it as a genuine conflict rather than a
silent no-op. My guess: whatever run landed MA's last real data (the one that set
`latest_bill_update` to 2026-09-03) already imported this roll call, and re-walking the same
bill/session in this run produced a record that doesn't hash identically -- but that's a guess,
not confirmed against the importer's actual dedupe-key construction logic.

**Verified directly against RDS: nothing changed.** `opencivicdata_jurisdiction.latest_bill_update`
for Massachusetts is still `2026-09-03`, unchanged by either attempt -- this run's real data has
NOT landed.

**Did not push further.** `cloud_loader.py`'s own docstring already flags that it has no
equivalent to `run-scrape.sh`'s `--allow_duplicates` override -- there's no supported "force
past this" path here even if that were the right call, and I don't think it obviously is: the
mismatch could indicate a real upstream problem (something changed about how this run's
`dedupe_key` gets built vs. MA's earlier one) rather than a case where forcing the import
through would be safe. Holding here rather than guessing at a fix on live production vote-event
data.

**Needs a real decision from someone who can reason about the importer's dedupe-key
construction** (or the specific history of how this roll call was first imported) -- not
something I should improvise around. Happy to keep digging (e.g., pull the actual existing DB
row for this vote_event and diff it against the incoming one) if that's useful, but wanted to
report the real blocker rather than keep retrying blind.
