# OPEN-385: Utah 2026 topics coverage (what the broker holds, and why the rest is missing)

Date: 2026-10-21. Read-only queries against production (`ddp-prod-rds-readonly`) and ddp-sync's log on the Mac. Nothing was changed by this investigation. **This is a snapshot taken while a ddp-sync run for UT 2026 is still in progress** (see "Still running"); the figures below are the floor, not the final count.

## Answer

**Status: partial.** As of 2026-10-21 ~12:15 EDT the ticket's acceptance ("the 669 bills are covered, or a stated reason for the remainder") is met for 356 bills, explained for 235, and open for 101. Not met until the in-progress run ends.

Utah 2026 has 1,016 bills in the broker. **234 of them have no version records at all**, so there is no text for LegBot to read and no topics can be generated until their text is archived and loaded.

### The 669, reconstructed from the broker

The ticket's 669 comes from ddp-sync's log (1,022 bills seen minus 341 with topics minus 12 failed), and the log's bill IDs are not kept here. The broker-side equivalent is "bills with no `bill_topics` artifact generated before 2026-10-16" (324 bills had one), which gives **692** bills, not exactly 669 (the log and the broker differ by a few bills on both the baseline, 341 vs 324, and the total, 1,022 vs 1,016). Their disposition now:

| Disposition | Bills |
|---|---|
| Now covered (topics generated since 2026-10-16) | 356 |
| No version records in the broker: no topics possible | 234 |
| Has text, no topics yet (the in-progress run has not produced them; not shown to be skipped or ineligible) | 101 |
| Has versions but none with a text URL, no topics | 1 |
| **Total** | **692** |

| Group (production, 2026-10-21 ~12:15 EDT) | Bills | With topics |
|---|---|---|
| No `BillVersion` rows in the broker | 234 | 0 |
| Versions exist, none with a text URL | 21 | 20 |
| Versions with text | 761 | 660 |
| **Total** | **1,016** | **680** |

`bill_topics` artifacts for UT 2026: 681, all `complete` and `approved`, **0 failed**. Artifacts are per bill version, topics per bill: one bill (`bfae0eaf-5c25-414d-af2a-bfd5a85d1865`) has two artifacts, so the unique-bill count, 680, is the coverage figure. The 12 failures in SYNC-123's table are not reproduced: none are recorded in the broker now.

**Utah row for SYNC-123's table** (unique bills, broker, 2026-10-21 ~12:15 EDT, run in progress): 1,016 bills; 680 with topics; 0 failed; 234 with no text; 102 with versions but no topics (101 with text, 1 without a text URL).

## What happened since SYNC-123's table (2026-10-16)

SYNC-123 counted 341 bills with topics, from ddp-sync's log (why it differs from the broker's 324 was not investigated). The broker held 324 bills with topics before 2026-10-16 (323 generated 2026-10-13, 1 on 2026-08-30). A ddp-sync session-pipeline run for UT 2026 (all artifact types including `bill_topics`, run id `6f89040c`) started 2026-10-21 00:47; it has produced 357 artifacts for 356 new bills so far (the 357th is the second artifact of the one bill above). No extra run was started for this ticket: a second run would collide with it.

## Sample check

Twelve bills picked at random (by `md5(gov_id)`) from all 680 covered bills, title against topics (`*` = primary):

| Bill | Title | Topics |
|---|---|---|
| HB152 | Educational Vaccine Exemption Amendments | Medical; Education* |
| HB47 | Vehicle Registration and Insurance Amendments | Government; Transportation* |
| SB66 | Medical Cannabis Pharmacy License Amendments | Medical; Business; Drugs* |
| HB448 | Utah Schools for the Deaf and Blind Amendments | Government; Education* |
| SB158 | Recreational Therapy Program Amendments | Medical*; Social Welfare |
| SB232 | Regulatory Impacts on Families | Social Welfare; Education; Government* |
| SB196 | Wrongful Lien Act Amendments | Housing*; Government |
| HB320 | Office of Artificial Intelligence Policy Amendments | Government; Technology* |
| SB76 | Residential Rental Payment Reporting Amendments | Housing*; Business |
| HB11 | Dyed Diesel Fuel Search Amendments | Transportation*; Taxes; Criminal Justice |
| HB319 | Electronic Records Amendments | Public Records*; Government; Technology |
| SB229 | State Employee Benefits Amendments | Government; Employment* |

All twelve read as reasonable. The weakest are HB152 (a vaccine-exemption bill whose primary is Education, not Medical) and SB232 (primary Government); both are defensible and neither is wrong.

## Still running

The 102 bills with versions and no topics (101 with text, 1 without a text URL; by type HB 61, SB 35, HJR 3, HCR 1, HR 1, SJR 1) have not been produced by the in-progress run. The note does not show why: they may only be pending, or the run may skip them. At 12:02 EDT the run's log had been silent since 10:59 behind one long changelog inference (inference timeout 10,000 s), so it may be slow rather than dead. When the run ends (`session_pipeline_run_end` for run `6f89040c`), re-run the group table above; whatever is still uncovered gets a targeted `bill_candidates` run (the SYNC-126 approach), and its failures are checked for ceremonial texts. Until then the Utah figures are a floor and this ticket is not finished.

## The 234 bills with no text

These need their version text archived and loaded into the broker first (the scrape/archive path, not LegBot). That is outside this ticket; it is a separate fact SYNC-123's table did not show. Utah topic alerts stay thin for those bills until that is done.
