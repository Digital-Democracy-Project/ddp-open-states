# OPEN-385: Utah 2026 topics coverage (final)

Date: 2026-10-21. Read-only queries against production (`ddp-prod-rds-readonly`) and ddp-sync's log on the Mac. Nothing was changed by this investigation. The topics were produced by ddp-sync's own session-pipeline run `6f89040c` (UT 2026, all artifact types including `bill_topics`), which started 2026-10-21 00:47 and logged `session_pipeline_run_end` at 15:35:38 (`bills_considered=1016 bills_processed=1016 truncated=False`, 53,277 s).

## Answer

**Done.** Every Utah 2026 bill now has topics: **1,016 of 1,016**, 0 failed. No targeted `bill_candidates` run was needed, and none was started: the run covered everything.

| Production, after the run ended (2026-10-21, after 15:35) | Bills | With topics |
|---|---|---|
| Utah 2026 | 1,016 | 1,016 |

`bill_topics` artifacts for UT 2026: 1,017, all `complete` and `approved`, 0 failed. Artifacts are per bill version, topics per bill: one bill (`bfae0eaf-5c25-414d-af2a-bfd5a85d1865`) has two artifacts, so the unique-bill count, 1,016, is the coverage figure.

**Utah row for SYNC-123's table** (unique bills, broker, after run `6f89040c` ended): 1,016 bills; 1,016 with topics; 0 failed; 0 never tried.

## The ticket's 669

The ticket's 669 comes from ddp-sync's log (1,022 seen minus 341 with topics minus 12 failed). The broker-side equivalent, "bills with no `bill_topics` artifact generated before 2026-10-16" (324 bills had one), is 692 bills (the log and the broker differ by a few bills on both the baseline, 341 vs 324, and the total, 1,022 vs 1,016; why was not investigated). All 692 are now covered: 693 artifacts were generated on 2026-10-21 (the 692 bills plus the one bill's second artifact). The 12 failures in SYNC-123's table are not reproduced: none are recorded in the broker now.

## Correction to this note's earlier draft

An earlier draft (mid-run, 12:15 EDT, when 680 bills had topics) said 234 bills "have no text, so no topics are possible until their text is archived and loaded". **That was wrong.** Those 234 bills had no `BillVersion` rows in the broker at the time; the run's first-sighting version backfill (SYNC-26) wrote them, and topics followed. Separately, an empty `text_url` on a broker version does not mean the pipeline had no text: 1,531 of Utah 2026's 4,457 broker versions have an empty `text_url` (including 542 `Enrolled` versions that got topics), and the pipeline evidently reads the text from elsewhere. So the draft's "no text URL" categories carry no meaning and are dropped.

## Sample check

Ten bills picked at random (by `md5(gov_id)`) from the 255 bills none of whose broker versions has a `text_url` (the group the earlier draft doubted; it includes most of the 234 that had no versions before the run), title against topics (`*` = primary):

| Bill | Title | Topics |
|---|---|---|
| HB434 | Child Welfare Fatality Review Report Amendments | Government; Public Records; Social Welfare* |
| SB66 | Medical Cannabis Pharmacy License Amendments | Medical; Drugs*; Business |
| HB206 | Nicotine Product Advertising Amendments | Media; Drugs*; Public Safety |
| HB523 | Homeless Services Land Use Amendments | Housing; Social Welfare*; Government |
| SB329 | Public Contracting and Boycott Amendments | Business; International Relations; Government* |
| HB576 | Child Welfare Timeline Compliance Amendments | Government; Social Welfare* |
| SB103 | Driver License Amendments for Unhoused Individuals | Housing; Transportation*; Social Welfare |
| HB403 | Transportation Corrections | Government; Transportation* |
| HB200 | Human Trafficking, Transporting, and Harboring Amendments | Criminal Justice*; Public Safety; Immigration |
| HB504 | Political Advertising Modifications | Elections*; Media; Technology |

All ten read as reasonable. This is a title-level check (topics against bill titles), not a read of the bill texts. An earlier random sample of twelve covered bills at 12:15 EDT also looked reasonable.

## Not done

- The Utah row of SYNC-123 is proposed above; SYNC-123 itself (closed) was not edited.
- Whether the run's 14.8 hours is acceptable for a full Utah session is not assessed here.
