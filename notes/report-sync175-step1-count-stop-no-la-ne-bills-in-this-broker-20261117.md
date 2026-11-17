# Report (read only, STOPPED at step 1): SYNC-175's row count does not match: this production broker holds no Louisiana or Nebraska bills

Written 19:51 UTC (date -u at write time). From the production EC2 host. Nothing was changed: no row rejected, no trigger sent, no backup needed. The stop condition "a row count that doesn't match" applies.

**What I read** (the broker on this host, through its web container; the two lists from your branch, 973 LA and 871 NE bills, all ids unique):
- None of the 973 LA ids and none of the 871 NE ids exists as a bill here (`Bill.primary_openstates_id`, found 0 of 973 and 0 of 871). The broker's bill rows for the three states: **LA 0, NE 0, AL 0 bills**, while NC has 2,343 and VA 848. So there are **0 bill_summary and 0 bill_changelog rows** for these lists on this host, not the counts you expected.
- Louisiana, Nebraska and Alabama exist as jurisdictions here, but their bills were never synced into this broker.
- So the LegBot results for LA/NE that you want rewritten are **not in this host's database**. They would live in the broker the website reads today, which BROKER-509 says is the Mac's dev broker, not this one. I can only act on this host's broker.

**What this means for the GO.** SYNC-175 as written (count, back up, reject, trigger the Mac's ddp-sync) has nothing to act on here. Which broker does the trigger's `X-DDP-Environment: prod` write to? If it writes to this one, the LA/NE bills would first have to exist here (they do not). I did not trigger anything to find out. OPEN-390 (NC first-time changelogs) is similar in that LegBot runs on the Mac, but NC does have 2,343 bills here; I have not counted its bill_changelog rows yet and will not start it until SYNC-175 is settled, per the GO's order.

**Ask:** tell me which broker holds the LA/NE results, or whether the rewrite is the Mac side's job. I will not reject or generate anything on this host without a clear answer.

## Also read (no action yet)
- 78b3ca4e4: the user's go for SYNC-175 then OPEN-390 was relayed; the user's own in-session words for these two are not given to me yet, so I would ask before any production change.
- 59c62e082: scrapers image v65 request; waits on Ramon registering it and a GO naming the revision. Its step A (the OPEN-556 state list on this host) is noted.
