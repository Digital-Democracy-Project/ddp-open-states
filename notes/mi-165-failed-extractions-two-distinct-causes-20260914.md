# MI's 165 failed text extractions -- two distinct, confirmed root causes, not one bug

While sizing up a possible manual MI LegBot pre-warm run, checked MI's real text-extraction
coverage: 13,432 of 13,597 archived documents (98.8%) have real extracted text; 165 (1.2%) are
`is_error=true` with no `raw_text`. Pulled the actual failing rows and inspected real S3
samples for both patterns found -- these are two separate, real, distinct bugs, confirmed by
opening the actual archived files, not just inferred from the error flag.

## Pattern A: 68 rows -- scraper captured the wrong page entirely (all "Substitute" versions)

`version_note` in `{Substitute (H-1), (H-2), (H-3), (H-4)}` -- 68 total. 61 of these 68 share
the **exact same source_url** (`https://legislature.mi.gov/Committees/CBR?committeeID=1980`)
and the **exact same sha256 content hash**, across completely different bills (HB 4101, HB
4153, HB 4235, ...). Downloaded and opened one directly:

```
<title>Committee Bill Records - Michigan Legislature</title>
```

**This is a generic committee bill-listing page, not the bill's actual substitute text.**
Confirmed, not inferred -- opened the real HTML. Extraction correctly has nothing real to
extract from; the scraper itself captured the wrong URL for these "Substitute" version types.
Fix belongs on the scraper side (resolve the real bill-specific substitute document URL for
these version types), not the extraction tool.

## Pattern B: 97 rows -- real content, extraction tool can't parse the format (all "Senate Enrolled Resolution")

Every one of the 97 `version_note="Senate Enrolled Resolution"` rows has a **distinct**
source_url and a **distinct** content hash (no duplication like Pattern A) -- these are
genuinely different real documents. Downloaded and opened one directly (SR 10):

```html
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" ...>
...
<h1>Senate Resolution No. 10</h1>
<p>Offered by Senators Santana, Chang, McMorrow, Moss, Anthony, Bayer, ...</p>
```

**This is real, complete, readable resolution text** -- sponsors, full body, everything a
normal extraction should have no trouble pulling out. The document uses an older XHTML 1.0
Transitional doctype with per-element inline CSS classes (`.s1`/`.s2`/`.s3`, custom font
families) for all text styling, rather than semantic tags -- my guess, not confirmed, is the
extraction tool's HTML parsing doesn't handle this specific template shape and comes back
empty/erroring even though the real text is sitting right there in the markup. This looks like
an extraction-tool gap, not a scraper problem -- the scraper got the right document both times.

## Why this matters for the MI LegBot pre-warm idea

165 bills would predictably fail LegBot dispatch with `no_archived_bill_text` regardless of
which fix (if any) lands first -- worth knowing going in rather than being surprised by 165
failures mixed into a much larger real-content batch. Not blocking a pre-warm run on this --
just flagging so the eventual failure count isn't mistaken for something new.

Full list of all 165 (identifier, version_note, source_url, archive_location, sha256, updated_at)
available on request if useful for a closer look -- kept this note to the two confirmed patterns
plus real samples since that's the actionable part.
