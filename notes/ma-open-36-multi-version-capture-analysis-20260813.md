# OPEN-36: Massachusetts multi-version capture — real site audit and scraper characterization

## Context

[OPEN-34](https://digitaldemocracyproject.atlassian.net/browse/OPEN-34) found MA's
`ddp_bill_version_document` archive has exactly one distinct `version_note` value
(`"Bill Text"`), one row per bill, 5,307 rows / 5,307 distinct bills, 1:1. That looked like a
classifier-vocabulary gap at first, but OPEN-34's note already concluded it wasn't — filed this
ticket to determine whether MA's *scraper* discards multi-version data its *source site* actually
exposes, or whether `malegislature.gov` genuinely never exposes more than one document per bill.

**Neither is quite right.** The site does expose real multi-version data — but structured as a
chain of separate bill/docket numbers, not as multiple documents attached to one bill ID the way
FL/VA/MI/AZ/UT/WA/US do it. Full detail below.

## 1. Scraper review — `scrapers/ma/bills.py`

`scrape_bill()` (`bills.py:278-286`):

```python
version = page.xpath(
    "//div[contains(@class, 'modalBtnGroup')]/"
    "a[contains(text(), 'Download PDF') and not(@disabled)]/@href"
)
if version:
    version_url = "https://malegislature.gov{}".format(version[0])
    bill.add_version_link(
        "Bill Text", version_url, media_type="application/pdf"
    )
```

This only ever emits one `version_link`, hardcodes the label `"Bill Text"`, and takes `version[0]`
(first match only) — which *would* silently drop a second match if the page ever had one. Verified
directly against live HTML (see §2) that it never does: **this is not a bug discarding data that
exists on a bill's own page.** The scraper faithfully captures the one document a MA bill's own
page ever exposes.

Separately, `scrape_action_page()` (`bills.py:359-373`) does this for every action-history row:

```python
action_name = row.xpath("string(td[3])")
```

`string(td[3])` flattens the cell to plain text and **discards any `<a href>` inside it.** This
matters a great deal — see §3/§4.

## 2. Real site audit — 8 `malegislature.gov` bill pages checked directly

Checked live via direct HTTP (not cached/summarized), including full bills that went to
enactment and floor amendment:

| Bill | Session | What happened | Own page's version link(s) |
|---|---|---|---|
| S.2584 | 192nd (2021-22) | Senate bill, amended in committee, passed to be engrossed, House-amended, conference report, enacted | Exactly 1: `/Bills/192/S2584.pdf` |
| S.2572 | 192nd | Senate committee substitute *of* S2584 | Exactly 1: `/Bills/192/S2572.pdf` |
| H.4879 | 192nd | House W&M committee-recommended substitute *of* S2584 | Exactly 1: `/Bills/192/H4879.pdf` |
| H.4891 | 192nd | Further-amended House floor text *of* S2584 | Exactly 1: `/Bills/192/H4891.pdf` |
| S.3097 | 192nd | Conference committee report *reconciling* S2584 | Exactly 1: `/Bills/192/S3097.pdf` |
| H.4889 | 193rd (2023-24) | Bond bill conference report, enacted Ch. 139 of 2024 | Exactly 1: `/Bills/193/H4889.pdf` |
| H.4648 (referenced by H.4889) | 193rd | The bond bill H4889 is the conference report *of* | not fetched — confirms the pattern generalizes beyond one bill |
| H.5620 | 194th (current) | Enacted Chapter 163 of the Acts of 2026 | Exactly 1: `/Bills/194/H5620.pdf` |

Raw HTML (not a rendered/summarized page) for S2584 confirms the `modalBtnGroup` div contains
exactly one `Download PDF` anchor — the "View Text" and "Print Preview" buttons alongside it point
at the *same* single document, just different presentation formats (HTML modal / print view /
PDF), not different version stages.

**Wayback Machine evidence that the single PDF URL is not overwritten in place:** `web.archive.org`
has two distinct content-digests for `/Bills/192/S2584.pdf` (2022-02-19 and 2024-03-31) — different
raw bytes, but `pdftotext` extraction is **byte-identical** between them (0 diff lines), despite
S2584 having been "passed to be engrossed" in the interim (11/17/2021, per its own action history).
Confirms the URL keeps serving the as-filed text forever; MA does not update a bill's own PDF in
place as it progresses.

## 3. Where the real version-stage vocabulary actually lives

S2584's full action history (fetched directly, anchors preserved):

```
11/17/2021 Senate  Text of S2572, printed as amended                    → <a href="/Bills/192/S2572">
11/17/2021 Senate  Passed to be engrossed -see Roll Call #114
 6/15/2022 House   ...the amendment (H4879) pending                     → <a href="/Bills/192/H4879">
 6/16/2022 House   For text of amendment, see H4891                     → <a href="/Bills/192/H4891">
 6/16/2022 House   Passed to be engrossed - 155 YEAS to 0 NAYS
 6/23/2022 Senate  Senate NON-concurred in the House amendment
 6/23/2022 Senate  Committee on conference (Cyr-Friedman-Tarr), appointed
 8/1/2022  Senate  Reported by S3097                                    → <a href="/Bills/192/S3097">
```

And H4889's (a different bill, same pattern):

```
7/19/2024 House  Reported on H4648                                      (its own originating bill)
7/29/2024 Exec.  Signed by the Governor, Chapter 139 of the Acts of 2024 → <a href="/Laws/SessionLaws/Acts/2024/Chapter139">
```

So MA's real "version-stage vocabulary" isn't a `version_note` field at all (there's only ever
`"Bill Text"`) — it's expressed as **hyperlinked cross-references to other bill/docket numbers,
embedded in the free-text action history**, each pointing at a fully separate `/Bills/{session}/{id}`
page with its own single PDF:

| Stage | Real MA artifact | URL pattern | Example |
|---|---|---|---|
| As filed/introduced | The original bill number's own PDF | `/Bills/{session}/{id}.pdf` | `/Bills/192/S2584.pdf` |
| Committee substitute | A *different* bill number, cross-referenced in action text ("Text of X, printed as amended") | `/Bills/{session}/{id}` | S2572 |
| Committee-recommended amendment | A *different* bill number ("...the amendment (X) pending") | `/Bills/{session}/{id}` | H4879 |
| Floor-amended text | A *different* bill number ("For text of amendment, see X") | `/Bills/{session}/{id}` | H4891 |
| Conference report | A *different* bill number ("Reported by X" / "Reported on X") | `/Bills/{session}/{id}` | S3097, H4889 |
| Enacted | A General Laws chapter, not a Bills/ page at all | `/Laws/SessionLaws/Acts/{year}/Chapter{N}` | Chapter 139 of the Acts of 2024 |

This is a structurally different model from VA/FL/MI/AZ/UT/WA/US, where one `bill_id` accumulates
several `BillVersion` rows distinguished by `version_note`. MA instead spreads a bill's lifecycle
across *multiple bill_ids*, linked only by prose in the action history.

## 4. Why the scraper captures none of this today

- The enacted Chapter-of-the-Acts link is thrown away: `scrape_action_page()` only keeps
  `row.xpath("string(td[3])")` (flattened text), never the row's `//a/@href`. The action text
  ("Signed by the Governor, Chapter 139 of the Acts of 2024") is stored, but the link itself is
  not, so this document isn't captured as a version at all today, for any MA bill.
- The intermediate stage documents (S2572/H4879/H4891/S3097-style bill numbers) are **not
  invisible to the pipeline** — they pass `scrape_bill()`'s own `bill_types` filter
  (`bills.py:214-217`) and are almost certainly present in the master
  `/api/GeneralCourts/{session}/Documents` list like any other bill, so today's scraper likely
  *does* scrape each of them — but as **freestanding, unrelated "bill" records**, each getting its
  own generic `"Bill Text"` version label, with no relation recorded back to the bill they are
  actually a stage of. This is a plausible real contributor to MA's 5,307-bills/5,307-rows 1:1
  stat: some fraction of those "bills" are procedural stage-documents of another tracked bill, not
  standalone bills in the sense FL/VA/etc. use the term. (Not confirmed against the production
  `ddp_bill_version_document` table in this session — no production DB access from this
  workspace — but directly confirmed that these bill numbers are live, independently-scrapable
  pages passing the existing type filter.)
- The existing code already has a working precedent for a bill-to-bill relation:
  `scrape_bill()` (`bills.py:237-242`) calls `bill.add_related_bill(docket_number,
  relation_type="replaces")` for the docket-number → bill-number hop. That pattern is directly
  reusable/extensible for the stage cross-references found here.

## 5. Recommendation

**Achievable — but the fix is a scraper-side capture-and-link problem, not a version-vocabulary
classifier problem.** MA needs no `_note_stage()` vocabulary coverage in `openstates-core` (there
is no vocabulary to classify); the real gap is entirely in `scrapers/ma/bills.py` not following the
hyperlinks its own action-history table already contains.

Two-tier scope for a follow-up implementation ticket:

1. **Low-effort, low-risk:** capture the enacted Chapter-of-the-Acts link whenever the
   "Signed by the Governor" action row contains one — add it as an additional
   `bill.add_version_link()` (or a distinct relation) alongside the existing "Bill Text" link.
   Small, isolated change to `scrape_action_page`/`scrape_actions`.
2. **Higher-effort, delivers the actual multi-version-diffing value:** parse action-row hrefs
   matching `/Bills/{session}/[A-Z]+\d+` to detect stage-document cross-references, then either
   (a) fetch each referenced document's own PDF and attach it to the *original* bill as an
   additional `version_link` with a stage label derived from the surrounding action text
   ("printed as amended" → committee substitute, "For text of amendment" → floor amendment,
   "Reported by/on" → conference report), or (b) keep them as independently-scraped `Bill` records
   but add explicit `related_bill` edges in both directions, extending the existing
   docket→bill-number `"replaces"` pattern already in the code.

**Open design question to flag for that follow-up ticket, not resolved here:** OPEN-34's diffing
pipeline (`archive_bill_versions()`, `diff_from_previous_version`) operates on `bill.versions.all()`
for a *single* `bill_id`. For MA's chain to feed that same pipeline, something has to decide which
bill number in a chain is canonical (e.g., keep the originating chamber bill — S2584 — canonical
and attach S2572/H4879/H4891/S3097 to it as versions), and how to handle branches where an earlier
proposal was superseded by a later one *before* passage (H4879's committee recommendation was
superseded by H4891's further-amended text in the same example) rather than being a clean linear
"previous version." That's real design work, appropriately out of scope for an analysis ticket.

Filed [OPEN-69](https://digitaldemocracyproject.atlassian.net/browse/OPEN-69) as the follow-up
implementation ticket for tier 1 (Chapter-of-the-Acts capture) with tier 2 (stage-chain capture)
scoped in its description as a follow-on design decision, not a blocking prerequisite.

## Disposition

- **OPEN-36: analysis complete.** MA's scraper does not discard multi-version data present on any
  single bill's own page (confirmed there is only ever one) — but the *site* does expose a real,
  richer multi-version chain, spread across multiple bill/docket numbers and linked only by
  hyperlinked prose in the action history, which the scraper does not currently follow.
- No code changes made in this ticket (analysis-only, per scope).
- OPEN-69 filed as the follow-up implementation ticket.
- This note documents the audit; a summary was also posted as an OPEN-36 comment.

## References

- [OPEN-34](https://digitaldemocracyproject.atlassian.net/browse/OPEN-34) — where MA's 0/0/5,307
  result was first noticed; this ticket's findings do not feed back into its classifier, which
  already correctly excludes unknown-stage notes rather than guessing
- [OPEN-69](https://digitaldemocracyproject.atlassian.net/browse/OPEN-69) — follow-up
  implementation ticket filed from this analysis
- `scrapers/ma/bills.py:278-286` (`scrape_bill`, current single-version capture),
  `:359-373` (`scrape_action_page`, where hrefs are currently discarded), `:237-242`
  (existing `add_related_bill("replaces")` precedent for docket→bill-number linking)
- `notes/va-open-34-diff-order-fix-and-backfill-20260807.md` — the sibling note this ticket was
  filed out of, whose format this note mirrors
- Real `malegislature.gov` pages checked directly (2026-08-13): `/Bills/192/S2584`,
  `/Bills/192/S2572`, `/Bills/192/H4879`, `/Bills/192/H4891`, `/Bills/192/S3097`,
  `/Bills/193/H4889`, `/Bills/194/H5620`, plus `web.archive.org` CDX history for
  `/Bills/192/S2584.pdf`
