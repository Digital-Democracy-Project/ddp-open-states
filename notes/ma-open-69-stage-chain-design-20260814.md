# OPEN-69: MA stage-chain capture — what shipped, what's deferred, and why

## Context

[OPEN-69](https://digitaldemocracyproject.atlassian.net/browse/OPEN-69) is the follow-up
implementation ticket from
[OPEN-36](https://digitaldemocracyproject.atlassian.net/browse/OPEN-36)'s analysis (full evidence
in `notes/ma-open-36-multi-version-capture-analysis-20260813.md`, same directory). That note
found `scrapers/ma/bills.py`'s `scrape_action_page()` discarded every `<a href>` in the action
table, losing two real signals: an enacted Chapter-of-the-Acts link on "Signed by the Governor"
rows (Tier 1), and cross-references to other bill numbers that are committee-substitute/
amendment/conference-report stages of the same legislative effort (Tier 2).

This note documents the Tier 2 design decision the ticket asked for: option (b) (related-bill
edges) is implemented now; option (a) (fetch each referenced PDF, attach as a version with a
derived stage label) is explicitly deferred, and the canonical-bill question OPEN-36 flagged is
still open pending product input.

## What shipped

**Tier 1** — `scrape_action_page()` now extracts every href in each action row's third cell. A
href matching `/Laws/SessionLaws/Acts/{year}/Chapter{N}` triggers
`bill.add_citation("Acts of Massachusetts", f"Chapter {N} of the Acts of {year}", "chapter", url=..., effective=action_date)`.
This mirrors `scrapers/de/bills.py:309-329`, which already does the identical thing for Delaware's
own `SessionLaws/Chapter` link, and reuses `citation_type="chapter"` — a value that already exists
in `openstates-core`'s `CITATION_TYPE_CHOICES` (`data/common.py:131-136`) for exactly this purpose.
`add_version_link` was deliberately *not* used: a direct fetch of
`/Laws/SessionLaws/Acts/2024/Chapter139` during this work confirmed the page is plain HTML with no
PDF at all, so treating it as a `bill.versions` entry would risk it being swept into OPEN-34's
PDF-diffing pipeline (`archive_bill_versions`/`diff_from_previous_version`), which only makes sense
for actual bill-text PDFs.

**Tier 2 (option (b) only)** — the same href loop also matches `/Bills/{session}/{bill-id}`
(anchored so it excludes `/CoSponsor`, `/BillHistory`, `/Bills/GetAmendmentContent/...`, etc.). For
each distinct match, not equal to the bill's own identifier, and not already present in
`bill.related_bills`, it calls
`bill.add_related_bill(ref_bill_id, legislative_session=bill.legislative_session, relation_type="related")`
— extending the existing docket→bill-number precedent at `bills.py:237-242`
(`add_related_bill(relation_type="replaces")`).

`relation_type="related"` was chosen deliberately, not `"replaces"`/`"replaced-by"`. MA's
`BILL_RELATION_TYPES` enum (`openstates-core data/common.py:78-84`) is `companion / prior-session /
replaced-by / replaces / related` — none of those five values encode "committee substitute" vs.
"floor amendment" vs. "conference report," and asserting a `replaces`/`replaced-by` direction here
would mean picking a canonical bill, which is exactly the open question below. `"related"` records
the graph edge without asserting supersession semantics the evidence doesn't yet support.

## Reciprocity finding (the spike this ticket called for)

OPEN-36's note flagged, but didn't check, whether these cross-references are reciprocal. This
ticket fetched four of the real stage bills' own action histories directly (session 192, the same
chain OPEN-36 audited from S2584's side) to find out:

| Bill | Own history's cross-reference | Links back to S2584? |
|---|---|---|
| S2584 (original) | → S2572, H4879, H4891, S3097 (all four, forward) | n/a (it's the source) |
| H4891 (further-amended floor text) | → H4879 only ("H4879, published as amended") | **No** |
| S2572 (committee substitute) | → S1276 only ("Recommended new draft for S1276" — a *third*, unrelated docket, not S2584) | **No** |
| S3097 (conference report) | → S2584 ("Reported on S2584") | **Yes** |

**Conclusion: reciprocity is not uniform.** Conference reports happen to link back to the
originating bill; committee substitutes and further-amended floor text do not — S2572 links to a
different docket entirely. Because each bill is scraped and yielded independently (no shared
mutable state between one bill's scrape and another's, and a `Bill` is finalized once yielded), a
single scraping pass can only record what each bill's *own* action history actually contains. That
is what's implemented: edges are exactly as asymmetric as the site's own hyperlinks, not
artificially forced bidirectional. Making every edge here bidirectional would require either a
second pass across all scraped MA bills in a session (reconciling edges after the fact) or a
lookup service — out of scope for this ticket; flagged as a possible follow-up if this graph needs
guaranteed symmetry later.

## What's deferred, and why

**Option (a) — fetching each referenced bill's own PDF and attaching it to the original bill as an
additional `version_link` with a stage label derived from the action text — is not implemented.**
Two reasons:

1. There's no schema field to carry a stage label. `related_bills` entries are
   `{identifier, legislative_session, relation_type}` — no free-text note. Implementing option (a)
   as originally scoped ("stage label derived from surrounding action text") would need either a
   schema change (out of scope per this ticket's own AC — "no schema changes expected") or storing
   the stage label somewhere else entirely (e.g. as an `add_extra`/citation note), which is a new
   design decision, not a mechanical implementation of the existing pattern.
2. **The canonical-bill question from OPEN-36 is still genuinely unresolved and needs product
   input, not an engineering guess.** OPEN-34's diffing pipeline
   (`archive_bill_versions()`/`diff_from_previous_version`) operates on `bill.versions.all()` for a
   *single* `bill_id`. Attaching S2572/H4879/H4891/S3097's PDFs onto S2584 as versions would mean:
   - Deciding S2584 (the originating chamber bill) is canonical — reasonable by convention, but not
     validated against a case where the *docket* bill (not the introduced bill) is the one that
     should anchor the chain.
   - Deciding how to order H4879 and H4891 as "versions" of S2584 when H4879's committee
     recommendation was superseded by H4891's further-amended text *before either passed* — this
     is a branch, not a next-in-line supersession, and OPEN-34's diff pipeline has no concept of a
     superseded branch today.
   - Deciding what happens to S2572's own link to S1276 (a third docket) — is S1276 also folded
     into S2584's canonical chain, transitively? That's a real modeling question, not a data gap.

   Today's option (b) implementation is inert with respect to that pipeline: `bill.versions` is
   untouched by this ticket, so nothing downstream changes behavior. This is deliberate — it lets
   OPEN-69 ship real, low-risk graph data now (visible in `related_bills` for any consumer that
   wants it) without forcing an answer to a product question under ticket-scope time pressure.

**What resolving the canonical-bill question would unlock:** either (a) implementing the PDF-fetch
version (probably as a follow-up ticket, once there's a stage-label storage decision and a
supersession/branch model for OPEN-34's pipeline to consume), or (b) building a canonicalization/
aliasing table that maps stage bill-ids to one canonical bill-id purely for diffing purposes,
without touching how each bill is scraped and stored individually. Either path is now unblocked to
scope with product input using this note plus OPEN-36's evidence — no further site auditing should
be needed first.

## Known limitations of what shipped

- Cross-reference edges assume the referenced bill is in the *same* legislative session as the
  bill being scraped (`legislative_session=bill.legislative_session`), matching the same
  simplification the pre-existing docket→bill-number `"replaces"` call already makes
  (`bills.py:237-242` also doesn't validate the docket's actual session). All real examples audited
  in OPEN-36 and this ticket were same-session references; a genuine cross-session stage reference,
  if one exists, would be mislabeled with the wrong session string.
- Dedup is per-bill, per-scrape (checked against `bill.related_bills` as the loop runs), not
  cross-bill. If the same bill is somehow scraped twice in one run, duplicate edges are possible —
  same caveat that already applies to every other `add_*` call in this file.

## References

- `notes/ma-open-36-multi-version-capture-analysis-20260813.md` — full evidence this ticket was
  scoped from.
- `scrapers/ma/bills.py` — `scrape_action_page()` (href extraction, citation + related_bill
  capture), `scrape_bill()` (`:237-242`, the pre-existing `add_related_bill` precedent extended
  here).
- `scrapers/de/bills.py:309-329` — the existing `add_citation(..., "chapter", url=...)` precedent
  Tier 1 mirrors.
- `openstates-core/openstates/data/common.py` — `CITATION_TYPE_CHOICES` (:131-136),
  `BILL_RELATION_TYPES` (:78-84).
- Real `malegislature.gov` pages checked directly for this ticket (2026-08-14):
  `/Bills/192/H4891`, `/Bills/192/S2572`, `/Bills/192/S3097`'s own `BillHistory` AJAX endpoints
  (reciprocity spike), plus re-confirmation of `/Bills/193/H4889` and `/Bills/194/H5620`'s
  Chapter-of-the-Acts markup already audited in OPEN-36.
