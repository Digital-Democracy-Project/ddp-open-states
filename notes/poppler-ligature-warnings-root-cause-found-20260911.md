# Root cause of the poppler "ligature component" warnings -- found

Answering the question you punted from `notes/poppler-ligature-warnings-question-20260911.md`.
Root cause confirmed directly, not just hypothesized.

## What it is

The specific PDF that triggers a burst of these in `usa-full-archive-20260728.log` is
`BILLS-119s3617is.pdf` (a Senate introduced bill, govinfo.gov). It embeds a custom Type1C/CFF
font named **`Gpospec5`** — almost certainly a Government Publishing Office in-house typesetting
font (the name reads as "GPO spec[ial] 5"), alongside the normal body fonts (`DeVinne`,
`DeVinne-Italic`, `Times-Roman`, `Cheltenham-Bold`, etc. — all standard congressional bill
typefaces with ordinary Adobe glyph names).

Dumped `Gpospec5`'s actual embedded CFF charset directly (via `fontTools`, not guessed) and found
its internal glyph names are literally of the form `_15`, `_19`, `_0020`, `_0021`, `_0022`, ...
— non-standard names with an inconsistent mix of 2- and 4-digit zero-padding, interspersed with a
few ordinary names (`space`, `zero`, `one`, `at`, `A`, `B`, `C`, `D`, ...) and some odd
control-character-looking leftovers (`BEL`, `TAB`, `dotaccent`, `ring`). This isn't a font
generated to any standard glyph-naming convention (Adobe Glyph List) — it looks like an
internal/generated font from whatever composition system GPO used to typeset this bill, where
many glyphs got auto-assigned placeholder names during subsetting rather than proper names.

Poppler's `parseCharName()` has a ligature heuristic for names like `f_i` (glyph = ligature of
"f" + "i", split on `_`). It sees `_15`'s leading underscore, tries to parse it the same way,
finds nothing on the left of the `_` and a number on the right, and can't resolve either side —
hence "Could not parse ligature component". Confirmed this is exactly what's happening by
re-running `pdffonts`/`pdftotext` against the real fetched PDF and reproducing the identical
warning text, then tracing it to `Gpospec5` specifically (the other embedded fonts' `/Encoding
/Differences` arrays and internal charsets all use ordinary Adobe names — only `Gpospec5` has the
`_N` pattern).

## Why it's non-fatal (matches what you already found)

This fires at font/glyph-table parse time, not per-rendered-character, which is why it floods the
log (once per glyph-name lookup that ever touches this font's table, not once per bill). Since
`docs_refused=0` held for every affected jurisdiction, extraction output wasn't blocked. I did not
go further and check whether any specific rendered character that maps to one of these `_N`
glyphs comes out wrong/blank in the extracted text (a real correctness question, distinct from
"does extraction complete") -- flagging that as a real, open, lower-priority follow-up if it's
ever worth confirming, not something I checked.

## Bottom line

This is a property of certain GPO-produced PDFs (likely tied to whichever composition pipeline/era
produced this specific font), not a bug in this project's own extraction code. Nothing to fix here
unless a future investigation finds specific rendered text is actually wrong for characters that
map to `Gpospec5`'s `_N` glyphs.
