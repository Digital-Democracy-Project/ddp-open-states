# What's causing the poppler "ligature component" warnings? (Ramon's ask, punting to you)

Ramon asked what's behind the `Syntax Warning: Could not parse ligature component "N" of
"_N" in parseCharName` lines that have been showing up throughout this backfill's logs
(thousands of times on `us` in particular). These appear to be non-fatal -- every jurisdiction
that produced them still completed with `docs_refused=0` -- but he wants to understand the
actual cause rather than just note they're harmless.

## What I ruled out / checked before punting this

- Not itself a sign of a bug in this backfill's own code -- these come straight from
  poppler's own font-name-parsing (the message format matches poppler's
  `GfxFont::parseCharName()`, which handles ligature-style glyph names like `f_i` by
  splitting on `_` and resolving each side).
- Tried to reproduce directly against ~10 real sampled `us` PDFs (mix of `Introduced` and
  `Reported_in_House` versions) -- none of my samples happened to trigger it, and a quick
  `strings` check on their `/Differences` arrays showed standard Adobe glyph names (`/space`,
  `/parenleft`, `/A`, `/B`, ...), not the `_N` pattern. Wasn't able to catch a live example
  in the time I spent on it -- didn't want to burn more of it, especially with the `us`
  backfill retry itself in flight.

## My working hypothesis, unverified

The literal message text (`_10`, `_0020`, `_0021`, ...) suggests some embedded font
(probably in specific PDF-generation pipelines used for certain document types/eras) uses
non-standard subsetted glyph names of the shape `_N` (sequential index or hex codepoint)
rather than proper Adobe Glyph List names, and poppler's ligature heuristic misreads the
leading underscore as a component separator with an empty left-hand side, then fails to
resolve the numeric right-hand side. If real, this would be a property of specific source
PDFs (probably from a particular era/generator on congress.gov or a specific state site),
not something this pipeline is doing wrong -- but I couldn't confirm which documents or
producer actually cause it in the time I spent looking.

Worth digging into if it's useful context for anything downstream (OPEN-269's document
handling, or just for Ramon's own understanding) -- not blocking anything in the current
backfill.
