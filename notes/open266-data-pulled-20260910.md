# OPEN-266 data pulled: MA excess is one homogeneous population, VA's 4 confirm your hypothesis

*Replies to `notes/open266-data-request-20260910.md`.* Pulled both, precisely rather than
sampled -- `_archive_path()`'s own bill-UUID-in-path convention let me exclude yesterday's exact
74 MA bills, not just estimate around them.

## MA: excluded yesterday's exact 74 bills, 100 true excess remain (not ~75 -- some bills
## contributed more than one row)

Extracted the real bill UUIDs from yesterday's `rev21` run's own `S3 upload failed for
bills/raw/ma/.../{identifier}--{uuid}/...` log lines (`_archive_path()` embeds the bill's
`ocd-bill/<uuid>` directly), then filtered MA's 149 `is_error=False`/null-`archive_location`
rows against that exact set -- **100 rows genuinely don't match any bill yesterday's run
touched.**

All 100 are strikingly homogeneous, not scattered across several historical events:
- **Same session for all 100**: `194th`.
- **Same `version_note` for all 100**: `"Bill Text"`.
- **Same URL shape for all 100**: `https://malegislature.gov/Bills/194/{HD|SD}NNNN.pdf`.
- `version_date` blank for all 100 (matches this codebase's own noted pattern of MA/VA often
  leaving it blank).

Sample of 10 (all 100 look the same shape):
```
HD 6108 | Bill Text |  | https://malegislature.gov/Bills/194/HD6108.pdf
SD 2684 | Bill Text |  | https://malegislature.gov/Bills/194/SD2684.pdf
HD 4819 | Bill Text |  | https://malegislature.gov/Bills/194/HD4819.pdf
...
```

This doesn't look like several small independent failures scattered across MA's weekly runs
since 2026-08-10 -- one consistent `version_note`/URL pattern across 100 bills reads more like a
single systemic gap specific to `"Bill Text"`-type MA documents (a filed-bill's own text, as
opposed to `Chapter_Law_Text_Enacted` etc.) never getting archived at all, possibly from before
the archiver started covering this document type, or a bug specific to that one `version_note`.
Worth someone checking whether `"Bill Text"` MA documents have ever successfully archived
(`archive_location` not null) for comparison -- I didn't check that count, easy to pull if useful.

## VA: all 4 rows fit your OPEN-33 hypothesis exactly

```
SB 759 | 2026 | Finance and Appropriations Substitute |  | .../1146801.PDF | is_error: False
SB 759 | 2026 | Chaptered                              |  | .../1222698.PDF | is_error: False
SB 759 | 2026 | Enrolled                               |  | .../1213247.PDF | is_error: False
HB 1320 | 2026 | Appropriations Substitute              |  | .../1142533.PDF | is_error: False
```

All `is_error=False` (extraction currently succeeds) with `archive_location` still null --
exactly the shape your hypothesis predicted: OPEN-33's direct in-place DB update fixed
`raw_text`/`is_error` without ever touching `archive_location`, so a document whose *original*
S3 upload also failed (independent of the extraction bug OPEN-15 fixed) would look exactly like
this. Confirmed, not just plausible -- two real bills (`SB 759`, `HB 1320`), both 2026 session.

## Not deciding disposition, per your note

Both are now real, specific, checkable facts rather than "some old rows somewhere" -- MA's 100
look like one systemic `"Bill Text"`-type gap worth its own look, VA's 4 confirm a small,
already-understood straggler from OPEN-33. Handing back to whoever owns OPEN-266's scope
decision.
