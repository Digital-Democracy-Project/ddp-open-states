# OPEN-385: Utah 2026 topics coverage (what the broker holds, and why the rest is missing)

Date: 2026-10-21. Read-only queries against production (`ddp-prod-rds-readonly`) and ddp-sync's log on the Mac. Nothing was changed by this investigation. **This is a snapshot taken while a ddp-sync run for UT 2026 is still in progress** (see "Still running"); the figures below are the floor, not the final count.

## Answer

The 669 "never asked" bills are mostly not a topics-run problem. Utah 2026 has 1,016 bills in the broker. **234 of them have no version records at all**, so there is no text for LegBot to read and no topics can be generated until their text is archived and loaded. Of the other 782 bills, 680 now have topics and 102 do not yet.

| Group (production, 2026-10-21 ~12:15 EDT) | Bills | With topics |
|---|---|---|
| No `BillVersion` rows in the broker | 234 | 0 |
| Versions exist, none with a text URL | 21 | 20 |
| Versions with text | 761 | 660 |
| **Total** | **1,016** | **680** |

`bill_topics` artifacts for UT 2026: 681, all `complete` and `approved`, **0 failed**. The 12 failures in SYNC-123's table are not reproduced: none are recorded in the broker now.

## What happened since SYNC-123's table (2026-10-16)

SYNC-123 counted 341 bills with topics. Production had 324 topic artifacts on 2026-10-13, then a ddp-sync session-pipeline run for UT 2026 (all artifact types including `bill_topics`, run id `6f89040c`) started 2026-10-21 00:47 and has added 357 so far. No extra run was started for this ticket: a second run would collide with it.

## Sample check

Twelve bills picked at random (by `md5(gov_id)`), title against topics (`*` = primary):

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

The 102 bills that have text and no topics yet (HB 61, SB 35, HJR 3, HCR 1, HR 1, SJR 1) are what the in-progress run has not reached. At 12:02 EDT the run's log had been silent since 10:59 behind one long changelog inference (inference timeout 10,000 s), so it may be slow rather than dead. If those 102 are still uncovered after the run ends, run `bill_topics` on them with a targeted `bill_candidates` list (the SYNC-126 approach); until then the Utah figures above are a floor.

## The 234 bills with no text

These need their version text archived and loaded into the broker first (the scrape/archive path, not LegBot). That is outside this ticket; it is a separate fact SYNC-123's table did not show. Utah topic alerts stay thin for those bills until that is done.
