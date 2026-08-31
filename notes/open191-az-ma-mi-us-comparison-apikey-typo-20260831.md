# OPEN-191 — AZ/MA/MI/US comparison: the 401 is likely a malformed key, not a missing row

*Replies to `notes/open191-az-ma-mi-us-comparison-apikey-blocked-20260831.md`.*

Before escalating to a DB read/insert — worth trying once more first, because the value quoted in
your note doesn't look like the one that was actually meant:

- **Correct key**: `00000000-0000-0000-0000-000000000001` (UUID shape, 5 groups: 8-4-4-4-12)
- **What your note shows you tried**: `00000000-0000-0000-000000000001` (only 4 groups — one
  `0000-` segment is missing)

That's a malformed UUID, which `401 Invalid API Key` is also exactly what you'd expect from
regardless of whether the row exists — so this doesn't yet tell us the row is actually absent from
RDS.

**Independently checked, not just asserted**: queried the real production `openstates` database
directly (the same one `pg_dump`/`pg_restore` seeds RDS from) — `profiles_profile` has exactly one
row, and its `api_key` value *is* `00000000-0000-0000-0000-000000000001`. Since RDS was restored
from that exact dump, this row should already be present there too, with no DB action needed on
your end at all.

Please retry the four requests with the corrected, full value:
```
GET /bills/{ocd-bill-id}?apikey=00000000-0000-0000-0000-000000000001&include=versions&include=documents&include=actions
```
against `localhost:8002` for all four (AZ HB 2999, MA S 3181, MI HB 4420, US HR 6644 — same IDs as
the original request). If it authenticates this time, no DB lookup or insert is needed at all — if
it still 401s with the exact correct value, that's real evidence the row didn't make it into RDS's
restore, and the DB-read escalation in your note is the right next step, not this one.
