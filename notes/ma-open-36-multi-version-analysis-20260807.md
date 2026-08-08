# OPEN-36: Massachusetts multi-version analysis — one text per bill number is the site's model, not a scraper bug; the version history lives elsewhere

## Context

[OPEN-34](https://digitaldemocracyproject.atlassian.net/browse/OPEN-34)'s cross-jurisdiction
`recompute-diff-order` backfill left Massachusetts completely untouched (0 corrected / 0 nulled /
5,307 unchanged) because MA's archive has exactly one distinct `version_note` (`"Bill Text"`),
exactly one per bill — 5,307 rows, 5,307 distinct bills, a perfect 1:1 ratio. No previous version
exists to diff against, regardless of classifier coverage. OPEN-36 asked: is the scraper
discarding multi-version data the site has, or does `malegislature.gov` genuinely not expose
version-stage documents? **Answer: both conclusions are true at once — the bill page really does
have only one text, and the scraper really does capture everything that page offers; but
multi-stage text absolutely exists on the site, in a structurally different shape than any other
tracked jurisdiction.** Analysis performed 2026-08-07 against the live site (194th General
Court); no code changed.

## AC1 — what the scraper does

`openstates-scrapers/scrapers/ma/bills.py`, `scrape_bill()`:

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

One version per bill by construction: the single "Download PDF" button on the bill page, with a
**hardcoded** `"Bill Text"` note. The 1:1 archive shape is exactly what this code must produce.
But it is *not* discarding a version list — the page has no version list to discard (see AC2).
What it does leave on the table: floor-amendment full text (available in the site's JSON API),
the document-chain links tying a bill to its redrafts (partially captured — docket→bill only,
via the `add_related_bill(..., relation_type="replaces")` call), and the enacted chapter-law
text (a different page entirely).

## AC2 — what the site exposes, checked against 11 real documents

Checked live on 2026-08-07, all from the 194th General Court, deliberately including bills with
known amendment/engrossment/enactment history (most are 2025 chapter laws):

| Document | What it is | Key observation |
|---|---|---|
| H1 | Governor's FY2026 budget (GAA) | 0 amendments; start of the budget document chain |
| H4000 | House Ways & Means FY2026 budget redraft | **1,658 floor amendments** in the API; still one bill text on the page |
| H4001 | House-passed FY2026 budget | History opens with **"H4000, published as amended"** — the post-amendment text is a *new document number*, then the Senate later "Amended by striking out all after the enacting clause and inserting in place thereof the text of S3" |
| S3 | Senate Ways & Means FY2026 budget | 1,058 floor amendments |
| H58 | Governor's FY2025 supplemental | 2 amendments; House amendment's API detail carries **full amendment text** and even its own document number (H61) |
| H4100 | Ch. 3 of 2025 (supplemental) | History: **"Reported on a part of H4003"** — an in-part committee redraft, new document number; page's "Similar Bills" links back to H4003 |
| S2521 | Ch. 4 of 2025 (supplemental) | Page has exactly one PDF link (`/Bills/194/S2521.pdf`) |
| S2575 | Ch. 14 of 2025 (supplemental) | `CommitteeRecommendations: "Compromised Version"` — the conference-report stage also lands as its own document |
| H972 | Ch. 15 of 2025 (MWRA/Lynnfield) | Full passage history incl. "Amendment adopted" + enactment; page still exposes exactly one text; enacted text lives at `/Laws/SessionLaws/Acts/2025/Chapter15` |
| H4004 | Ch. 18 of 2025 (Hardwick election) | Ordinary docket→bill chain (HD4539 → H4004) |
| H2 | Governor's FY2027 budget (just filed) | Fresh bill baseline: all API version-adjacent fields empty |

Conclusive negative, not just "we didn't find one":

- Every bill page checked (H972, H4100, S2521) exposes **exactly one** text: `/Bills/194/<id>.pdf`
  plus an HTML `/Bills/194/<id>/<Branch>/Bill/Text` view. No version list, no stage dropdown, no
  amended/engrossed/enrolled text links anywhere on the page.
- The branch segment of the text URL is decorative: `/Bills/194/H972/House/Bill/Text` and
  `/Bills/194/H972/Senate/Bill/Text` return **byte-identical** content (same md5,
  `c10ac65cfd7211e4aba68dda041a3e93`) — even though H972 had a House amendment adopted after
  engrossment. The page text never advances past the as-introduced document.
- The per-document JSON API (`/api/GeneralCourts/194/Documents/<id>`) has no version array
  either. Its version-adjacent fields are `Amendments`, `Attachments`,
  `CommitteeRecommendations`, and `DocumentText` (the *one* text, when populated) — nothing that
  enumerates stage texts for the same document number.

**A bill number in Massachusetts is one immutable text.** When the text changes, Massachusetts
issues a *new document number*. This is a hard structural property of the source, so per-bill
1:1 versions are permanent under the current scraper model — no amount of scraping the bill page
harder will ever produce a second version row.

## AC3 — where MA's version history actually lives (the "vocabulary" audit)

MA has no `version_note` vocabulary to audit in the OPEN-34 sense — its stage vocabulary lives
in **history-action language and document-chain links** instead:

1. **Stage = new document number**, linked by history actions and API fields:
   - Docket → bill: `HD3492` → `H972` (the scraper already records this as a `"replaces"`
     related bill).
   - Committee redraft: *"Reported on a part of H4003"* (H4100); the classic phrasing for
     ordinary bills is *"Accompanied a new draft, see H…"*. Also surfaced structurally in the
     API's `CommitteeRecommendations` (which reference the successor/predecessor bill objects).
   - Post-floor-amendment published text: *"H4000, published as amended"* (as H4001's first
     history line).
   - Cross-chamber substitution: *"Amended by striking out all after the enacting clause and
     inserting in place thereof the text of S3"*.
   - Conference/compromise: `CommitteeRecommendations.Action = "Compromised Version"` (S2575).
2. **Floor amendments carry full text in the JSON API**, not on the bill page:
   `/api/GeneralCourts/194/Documents/<bill>/Branches/<Branch>/Amendments/<n>/` → `Text` field
   (verified on H58's House amendment №1; H4000 has 1,658 of these).
3. **The enacted text is a session-law page**, not a bill document:
   `/Laws/SessionLaws/Acts/<year>/Chapter<N>`, discoverable from the terminal history action
   *"Signed by the Governor, Chapter 15 of the Acts of 2025"*. Verified the Chapter 15 page
   carries the full statutory text.

So a "version lineage" for an MA law is a walk across documents, e.g. FY2026 budget:
`H1 → H4000 → (1,658 amendments) → H4001 → (Senate: text of S3) → conference → Chapter law`.
Note the in-part redrafts (one governor's bill reported out as *several* bills) make this a
**DAG, not a chain**.

## AC5 — recommendation

Two tiers, deliberately separable:

- **Tier 1 (recommended, cheap, high-value): scrape the chapter-law text as a second version on
  enacted bills.** The terminal history action names the chapter; the session-law URL is
  deterministic from it. One extra fetch per *enacted* bill (dozens per year, not thousands)
  yields an introduced-vs-enacted diff for every Massachusetts law — the diff that matters most.
  Requires adding MA's two stage notes (`"Bill Text"`, new enacted note) to `_note_stage()`'s
  table in `openstates-core` so the OPEN-34 classifier ranks them (currently both would be
  excluded as unknown-stage).
- **Tier 2 (defer, file separately only if wanted): document-chain lineage reconstruction.**
  Walking redraft/engrossment/substitution links to attach stage texts as versions of one
  canonical bill crosses OpenStates' one-`Bill`-object boundary — the stage texts legitimately
  *are* different bills in MA's model, the in-part DAG has no single canonical ancestor, and
  cross-chamber substitution ("text of S3") aliases documents across chambers. This is a data-
  modeling decision (probably DDP-side, on top of `related_bills`), not a scraper patch. Don't
  bundle it with Tier 1.
- Amendment-text capture (`add_document_link`, not versions) is a possible bonus in Tier 1's
  follow-up but adds volume (1,658 on H4000 alone) for unclear diff value — noted, not
  recommended now.

Follow-up implementation ticket for Tier 1:
[OPEN-37](https://digitaldemocracyproject.atlassian.net/browse/OPEN-37).

## References

- [OPEN-36](https://digitaldemocracyproject.atlassian.net/browse/OPEN-36) — this analysis ticket
- [OPEN-34](https://digitaldemocracyproject.atlassian.net/browse/OPEN-34) /
  `notes/va-open-34-diff-order-fix-and-backfill-20260807.md` — where MA's 1:1 shape was noticed;
  the stage classifier Tier 1 must extend
- `openstates-scrapers/scrapers/ma/bills.py` — `scrape_bill()`'s single-version capture,
  `scrape_bill_list()`'s use of the malegislature JSON API
- `https://malegislature.gov/api/GeneralCourts/<court>/Documents/<id>` (+
  `/DocumentHistoryActions`, `/Branches/<Branch>/Amendments/<n>/`) — the JSON API this analysis
  probed; returns JSON to non-browser user agents
- `ddp-infra/PLAN-bill-document-provenance.md` — the pipeline Tier 1 would extend
