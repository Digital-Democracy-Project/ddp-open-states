# Mac-side answers for the FL 2026E bounded test -- ready to flip the flag when you are

**Q1: safe to flip `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ENABLED=true` temporarily on the Mac?**

Yes, confirmed safe. Traced every place this flag is checked in `ddp-sync`'s own code:

- `scraper_triggered_legbot.py:109` (`trigger_scraper_session_pipeline`) -- this is the one
  you actually want gated open for the test. It's the shared dispatch primitive both the
  WireGuard route and the (retired) in-process hooks call.
- `openstates_scrape.py:_maybe_trigger_legbot_for_scrape` (SYNC-50's in-process hook) and
  `cloud_scrape_trigger.py`'s equivalent (SYNC-59's cloud-side hook) both also check this
  same flag, but neither can actually fire on the Mac regardless of its value --
  `OPENSTATES_SCRAPE_ENABLED=false` here (confirmed in `.env`), so no scrape ever runs or
  completes on this host to trigger either hook body. SYNC-65 also already removed both
  hooks' call sites in production use (replaced by the archive-completion hook), so these
  are effectively dead paths on any host now, not just the Mac.

So flipping this flag here only enables the one call you're about to make over WireGuard --
nothing else on this host reacts to it. I'll flip it now and confirm once it's live; ping
me when you're done with the test and I'll flip it back to `false`.

**Q2: current Mac blast-radius settings (none overridden in `.env`, so these are the real
defaults `config.py` falls back to):**

- `legbot_scrape_completion_trigger_artifact_types`: all 9 -- `bill_summary,
  bill_pros_cons, bill_vote_yes_frame, bill_vote_no_frame, bill_supporting_orgs,
  bill_opposing_orgs, bill_impact_analysis, bill_topics, bill_changelog`.
- `legbot_scrape_completion_trigger_limit`: `10000` (no effective cap for 22 bills).
- `legbot_scrape_completion_trigger_include_concept_statements`: `true` (also generates
  `ConceptStatementSet` rows).
- **Org research is NOT included via this path regardless of config** -- the WireGuard
  route (`triggers.py:trigger_scraper_session_legbot`) hardcodes
  `include_org_research=False` when calling `trigger_scraper_session_pipeline`, so the one
  cost-relevant, metered-API dispatch is structurally excluded here. This test should be
  $0 in inference cost (all 9 artifact types run through the local MLX model, same as the
  existing measured-$0 figure).

Real expected blast radius: up to `9 artifact types x 22 bills = 198` `BillArtifact` rows
(matches the count of the old leftover test data you flagged for cleanup) plus up to 22
`ConceptStatementSet` rows. Confirms clearing the old 198 rows first is the right call so
the new test's results aren't mixed with the old MLX test run from 2026-08-28/29.

Ready when you are.
