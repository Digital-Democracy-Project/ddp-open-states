# Follow-up: Gpospec5 does NOT corrupt extraction or diffs (Ramon's follow-up question)

Closing the loop on `notes/poppler-ligature-warnings-root-cause-found-20260911.md` -- that write-up
flagged "does a rendered character actually come out wrong for a `_N` glyph" as an open question.
Checked it directly, on the same `BILLS-119s3617is.pdf`.

## Two independent reasons it's harmless

1. **The font's `/ToUnicode` CMap only maps 2 of its ~225 glyphs at all** -- codes `0x58`/`0x78`
   ("X"/"x"), matching this font's `/Encoding /Differences` array (`[88 /X 120 /x]`) exactly. Text
   extraction (`pdftotext`, and whatever this project's own extraction uses under the hood) reads
   character-code-to-Unicode through `ToUnicode`, not through the glyph's internal name -- so even
   where this font IS used, the extracted text is a correct "X"/"x" regardless of the other ~223
   glyphs' malformed `_N` names. The ligature-parse warning only fires while poppler builds the
   font's internal glyph-name table at load time; it has no bearing on what `ToUnicode` resolves.
2. **In this specific PDF, `Gpospec5` isn't actually used to paint any character at all.** Checked
   every page's content stream directly for the font's resource selector (`/F8 ... Tf`) -- zero
   hits across the whole document. It's declared as a font resource (likely inherited wholesale
   from GPO's shared bill-template resource set, not requested per-document) but never invoked.
   `pdffonts` lists it because it's embedded and declared, not because anything on the page uses
   it.

Either fact alone would be enough; both hold. **No extraction or diff corruption from this font,**
in this document and, by the same ToUnicode-independent-of-glyph-name reasoning, in any other bill
that happens to actually use it too.
