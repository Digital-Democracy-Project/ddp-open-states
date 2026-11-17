# Note on SYNC-175 (follows de0ae9d0a): there can be no summary or changelog rows for LA and NE until LegBot has run for those states

Written 20:17 UTC (date -u at write time). From the production EC2 host; the user asked me to pass this on. Nothing was changed.

The user's point: `bill_summary` and `bill_changelog` rows are created only by a LegBot run, so a state LegBot has never run for cannot have any. That matches what I read: this host's broker has **0 Louisiana, 0 Nebraska and 0 Alabama bills and therefore 0 artifacts for them** (NC has 2,343 bills, VA 848). The count in de0ae9d0a is not a data fault here; it is the expected state of a broker LegBot has not touched for LA and NE.

So SYNC-175's premise, rewriting existing LegBot results for 973 LA and 871 NE bills, does not hold on this host. If results for those bills exist anywhere, they are in another broker (the Mac's); I cannot read it. Please check, on your side, where the LA/NE results you listed were written, and tell me which broker the real run should target. I am not rejecting, generating or triggering anything for LA or NE on this host until you do.
