# MI's 165 failed extractions: real LegBot impact is only 17, not 165

Follow-up to `mi-165-failed-extractions-two-distinct-causes-20260914.md`. Ramon asked how
these 165 would actually be handled if we ran a real LegBot pass against MI now -- checked by
directly calling the exact resolution function LegBot itself uses
(`get_archived_bill_text`/`_resolve_bill_source`, `local_openstates_client.py`) against the
RDS-backed api-v3 for all 165 real bills, not sampling or inferring.

**148 of the 165 would dispatch successfully anyway.** `get_archived_bill_text` doesn't read
the one specific failed document -- it resolves the bill's *current version* and checks every
link attached to that version, so if a different link/version's document extracted cleanly,
it's used transparently. The failed document being unusable doesn't matter for these 148 as
long as their current version has at least one other working link.

**17 would genuinely fail with a clean `no_archived_bill_text`** (verified against every one
of the 165, not extrapolated from a sample):

```
HB 4399, HB 4813, HB 4385, HB 4834, HB 4878, HB 4894, HB 4954, HB 5358, HB 5434, HB 5435,
HB 5252, HB 5356, HB 5518, HB 5558, HB 5774, HB 5943, SR 99
```

16 of the 17 are House "Substitute" bills, 1 is a Senate resolution (SR 99) -- roughly a 24%
real failure rate within the 68 "Substitute" pattern specifically, versus only 1 of 97 for the
"Senate Enrolled Resolution" pattern (SR 99 itself). Consistent with the two-cause split
already reported: the "wrong page captured" bug (Pattern A) more often leaves a bill with no
other usable link, while the "extraction tool can't parse this format" bug (Pattern B) usually
still has an earlier/alternate version's text available as a fallback.

**Net effect on the MI pre-warm plan**: 17 real, clean, cleanly-logged failures out of ~4,000
bills is a rounding error, not a blocker -- doesn't change the feasibility question, just
narrows exactly which bills would need the underlying extraction bugs fixed before they'd ever
get real content.
