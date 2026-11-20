# REQUEST (not a GO): OPEN-557, the stored session types for GA, VA and WA (a read-only check, then one guarded update), before api-v3 #72

Written 05:00 UTC 11-20 (Mac side, State Specific Handling). **Not a GO.** It replaces step C of `59c62e0` / `e5d12b9`; no prod note has reported that step.

## Why (the Mac replica, read 11-20 05:00 UTC)
- Scrapers #124 (every session list says regular or special) merged 11-17 19:45 UTC and is in every image since. **Oregon is clean (0 blank of 30). Georgia, Virginia and Washington still have blank types:**
  - GA: 14 of 14 sessions;
  - VA: 28 of 33, including both `2018specialI` rows (`e29664cd-…`, `9b394afc-…`);
  - WA: 6 of 9 (2009-2010 to 2019-2020).
- **So the nightly imports have not stored the types for these three states**, despite step C.1's assumption. Why is not yet known; my guess, not checked, is that the load takes the session list from somewhere other than the image's scrapers. **Do not wait for more imports: use the update below.**

## Order (it matters)
1. **Your api-v3 release `bc30545` (OPEN-660) can go first, as written: at `8cef03e4` exactly, not api-v3 main's head.** It does not contain #72. If you rebuild api-v3 from a later main for any reason, check that `fix/OPEN-557-stored-classification` is not in it; if it is, stop and report.
2. **This note, steps A to C**, each after Ramon's go.
3. **Only after step C reads clean** (on RDS here, and on the Mac replica on my side): Ramon merges api-v3 #72 (head `e5929ae`, main merged in, 580 tests pass), then an api-v3 rebuild on both hosts. **#72 released before step B would make Virginia's current session 2023 and leave Georgia with no previous session.**

## A. The check (read-only, RDS)
```sql
select substring(j.id from 'state:([a-z]{2})') st, count(*) filter (where coalesce(s.classification,'') = '') blank, count(*) total
  from opencivicdata_legislativesession s join opencivicdata_jurisdiction j on j.id = s.jurisdiction_id
 where j.id ~ 'state:(ga|or|va|wa)/' group by 1 order by 1;
```
- **Expect** the replica's numbers: ga 14/14, or 0/30, va 28/33, wa 6/9.
- If RDS differs, report and stop.

## B. The stored fix (one transaction, RDS, after Ramon's go)
The values are the scrapers' own lists (#124), so the next import would write the same.
```sql
begin;
update opencivicdata_legislativesession s set classification =
  case when s.identifier in ('2011_ss','2018_ss','2020_ss','2021_ss','2023_ss','2026_ss',
                             '2011specialI','2012specialI','2013specialI','2014specialI','2015specialI','2018specialI',
                             '2018specialII','2019specialI','2020specialI','2021S2','2022S1','2023S1','2024S1','2026S1')
       then 'special' else 'primary' end
  from opencivicdata_jurisdiction j
 where j.id = s.jurisdiction_id and j.id ~ 'state:(ga|va|wa)/' and coalesce(s.classification,'') = '';
-- expect UPDATE 48 (GA 14, VA 28, WA 6); any other count: rollback and report
commit;
```
- **Only blank rows are touched.** No other state, no other column.
- The two VA `2018specialI` rows both become `special`.

## C. Read back (read-only, RDS)
1. Run A again: **expect 0 blank** for all four states.
2. Then:
```sql
select substring(j.id from 'state:([a-z]{2})') st, s.classification, count(*)
  from opencivicdata_legislativesession s join opencivicdata_jurisdiction j on j.id = s.jurisdiction_id
 where j.id ~ 'state:(ga|va|wa)/' group by 1, 2 order by 1, 2;
```
**Expect:**
- ga: primary 8, special 6;
- va: special 15, primary 18 (the 5 rows already set stay as they are);
- wa: primary 9.

These are the counts the same rule gives on the Mac replica today. Report both results. I confirm on the Mac replica and then tell Ramon #72 can merge.

**Rollback** (only if needed): set `classification = ''` for the same 48 ids. Save `select s.id from … where … and coalesce(s.classification,'') = ''` before step B.

## Not authorized
Any other stored change, any import or scrape, merging any PR, an api-v3 rebuild from a main that contains #72.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
