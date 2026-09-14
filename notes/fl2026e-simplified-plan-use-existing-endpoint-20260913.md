# FL 2026E: simplified plan -- skip the code change, use the existing manual endpoint directly

Ramon's call: don't build new code on the automated archive-completion trigger path for
this. Just use `POST /trigger/bill-artifact-generation` directly -- it already accepts
`retry_failed` natively in its own request body, no deployment needed. (I'd started a PR
adding `retry_failed` support to the OTHER endpoint, `/trigger/scraper-session-legbot` --
closed it unmerged, ddp-sync PR #151, once we realized the simpler existing path already
covers this.)

**Plan:**

1. Mark the 198 old `BillArtifact` rows (the 8 types that never regenerated: everything
   except `bill_changelog`) `status=failed`.
2. Call `POST /trigger/bill-artifact-generation` (on the Mac's `ddp-sync`, same
   `X-DDP-Environment: prod` header as before) with:

```json
{
  "jurisdiction_iso2": "FL",
  "session_code": "2026E",
  "artifact_types": ["bill_summary", "bill_pros_cons", "bill_vote_yes_frame",
    "bill_vote_no_frame", "bill_supporting_orgs", "bill_opposing_orgs",
    "bill_impact_analysis", "bill_topics"],
  "include_org_research": false,
  "include_concept_statements": false,
  "limit": 25,
  "retry_failed": true
}
```

Notes on that payload:
- `bill_changelog` deliberately left out -- it already regenerated fine in both earlier
  archive-completion runs, no need to touch it again.
- `include_concept_statements: false` deliberately -- concept statements already got
  regenerated twice (the duplication issue from the earlier note); don't create a third
  batch.
- `include_org_research: false` -- keeps this at $0, matches the earlier test's cost
  profile.
- `limit: 25` -- comfortably above the real 22-bill count.

This endpoint calls `run_legbot_pipeline` directly (not the overlap-locked automated
wrapper), so no flag-flip/env-var dance needed on either side -- just the one request.
