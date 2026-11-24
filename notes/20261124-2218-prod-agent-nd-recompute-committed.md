# status: ND recompute-diff-order COMMITTED (3 flag changes); read 4e74c0d

Ramon's "go" in my session after my list naming this as the open item (22:08 UTC).

- Before: I re-fetched the notes (read 4e74c0d: MO verified, KY archive read, nothing asked of me beyond the MO archive end line and a peak resource reading) and re-ran the dry run: `nd: [DRY RUN] 1106 bills checked | unchanged=2690 corrected=0 nulled=0`, `is_bill_version set=0 changed=3 not_a_version=3`, baselines 0, list 0 documents (identical to the earlier one).
- Backup: ops/nd-docs-backup-20261124.csv (taken before the refresh; it holds each document's is_bill_version, so the three flags' old values are in it).
- Commit: `nd: [COMMITTED] 1106 bills checked | unchanged=2690 corrected=0 nulled=0`; `is_bill_version: set=0 changed=3 not_a_version=3`; `diff_baseline_id: set=0 changed=0 cleared=0`; `change list ... (0 documents)`; exit 0. As you said, the flag flips are not in the list, so nothing guards them; I checked them by reading afterwards.
- Read after (RDS, read only): the three "NOT ADOPTED" ND documents now read `is_bill_version = False`: SB 2308 "SECOND ENGROSSMENT - NOT ADOPTED", SB 2400 "SECOND ENGROSSMENT - NOT ADOPTED", SCR 4022 "FIRST ENGROSSMENT - NOT ADOPTED". They are the only ND documents whose note contains "NOT ADOPTED". A dry run afterwards reports `is_bill_version changed=0` (the not_a_version=3 figure is the stored count, not a pending change).
- Resource reading you asked for: not yet; I report the peak after the WY/NE/UT loads. Reading at 22:07: load 1.79 / 1.18 / 1.41, 7.0 of 15.7 GB.
