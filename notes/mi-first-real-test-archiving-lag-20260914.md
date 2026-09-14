# Michigan's first-ever real LegBot test: content quality is good, but most bills failed on a text-archiving lag, not a Bill-creation bug

Ran MI's first-ever real LegBot dispatch today (dev-checkout session, not the prod agent) -- a
bounded 50-bill sample against `2025-2026`, all 9 `ALL_ARTIFACT_TYPES` + `bill_changelog` +
`include_concept_statements=true`, `include_org_research=false`, via the on-demand
`POST /ddp-sync/v1/trigger/bill-artifact-generation` endpoint (`X-DDP-Environment: dev`, this
Mac's own dev broker). `run_id=8e6d606f5bb1454fa849069cd7cead2b`.

**Result: 10 of 50 bills came back completely clean, 5 more had 7-8 of 8 types succeed with one
real, honest `insufficient_information` decline, and 35 failed every type.** First guess (wrong,
corrected after re-checking the logs) was that ddp-broker's dev database didn't have Bill rows for
these bills. It does, and `ensure_bill_exists` works exactly as designed -- confirmed directly via
`Bill ensured ... created=True` log lines for every bill that succeeded.

**Real root cause, confirmed by comparing two actual bills directly:**
- **SB 1148** (one of the 35 failures, `bill_openstates_id=c6c62662-5e03-4d59-ba09-23df17b0b17f`):
  `first_action_date=2026-09-09` (introduced 5 days before this test), `created_at` in our own
  system `2026-09-13T02:18:08Z` (synced in yesterday). Real version metadata exists (a genuine
  "Senate Introduced Bill" with real PDF/HTML links), but `get_archived_bill_text` returns nothing
  -- no extracted text yet. Every one of its 8 non-changelog artifact types logged
  `No archived bill text -- recording a failed artifact` before the broker write was even
  attempted.
- **SB 855** (one of the 10 clean successes,
  `bill_openstates_id=70782809-4227-42b7-bade-dbdf57ea796f`): `first_action_date=2026-03-18`,
  months old, archived text present, all 9 types generated real content.

Breakdown by bill type among the 35 total failures: 28/39 SBs, 3/7 HBs, 4/4 SRs (Senate
Resolutions) -- not exclusively resolutions, real substantive Senate Bills are affected too, so
this isn't just "resolutions don't get archived by design."

**This is the same archiver-lags-scraper gap SYNC-65 exists to guard against** (the automated
trigger fires on archive completion specifically so it never hits a bill before its text is ready)
-- it surfaced here because this was a manual on-demand call that bypasses that gate entirely, not
because anything about the automated path is broken. Michigan-specific question worth someone with
real visibility into the archiver checking: is a ~5-9 day lag between a bill's introduction and its
text being archived normal/expected for MI on its current schedule, or is MI's archiver stuck /
running less often than intended? I don't have visibility into the archiver's own schedule or last-
run history from this session.

**The good news, since data quality was the actual point of this test**: the 10 (and effectively
15) bills that did have archived text produced genuinely good content, spot-checked directly against
the broker's real stored rows, not just the dispatch response. SB 855 (MI's EGLE/environment
department FY2027 budget, $945M) -- summary, pros/cons, and impact analysis all cited real dollar
figures pulled from the actual bill text ($406M water infrastructure, $9.6M lead service line
replacement, etc.), topics tagged Environment/Energy/Government correctly, concept statements were
specific and neutral. SB 871 (Licensing & Regulatory Affairs budget) was equally solid -- correctly
identified liquor/cannabis regulation, boiler inspection, indigent defense as covered, topics tagged
appropriately. No hallucinated figures or generic filler in either sample.

One smaller open item: `bill_changelog` was listed as "generated" for first-version bills in the
dispatch response but returns `{"found": false}` on the public read endpoint -- likely because a
bill's very first version has nothing to diff against and this correctly resolves to
"not applicable" rather than a real row, but I haven't confirmed that's actually what's happening
underneath rather than a silent write issue.

**Not asking you to fix anything here** -- flagging for whoever has real visibility into MI's
archiver schedule/health, since this session doesn't. If it's normal lag, nothing to do. If MI's
archiver is genuinely behind, that's worth knowing before MI's own allowlist entry
(`LEGBOT_RDS_REPLICA_JURISDICTION_ALLOWLIST` already includes `mi`) starts seeing real automated
dispatches once SYNC-65's trigger is actually enabled.
