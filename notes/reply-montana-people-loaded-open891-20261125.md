# Reply: Montana people load done (OPEN-891), 11-25 23:33 UTC

Ramon approved it in this session ("Yes, run it once"). People load only; no re-import, no scrape, no restart, no other state.

## Gates
* Quiet: no people run, no Montana job, no Montana pipeline lock (the locks held were for other states).
* Code: people checkout fast-forwarded to `02d992fd`. `ls data/mt/retired | grep -c Resigned` is 0; the real record carries `identifier: ocd-person/2c6a890f...` under `other_identifiers`.
* Gate 3: the only commit touching `data/mt` between the old checkout and `02d992fd` was `1ec603f41c` (#55). The same pull also brought 15 non-Montana files (CI workflow and test fixtures); none are loaded.

## Baseline (RDS, read-only, before)
* Junk person: 0 sponsorships, 0 votes. Real Doug Flament: 0 sponsorships, 0 votes. Montana people: 445.

## The load
* `--safe` first: 450 files, 0 created, 1 updated (the real Doug Flament), 1 removed via merge (junk id into the real id), nobody retired or missing. (`--safe` exits 1 on purpose: it cancels its own transaction.)
* Real load: same lines, 450 files, 0 created, 1 updated, exit 0.

## After
* The junk row is gone. Real Doug Flament: 0 sponsorships, 0 votes (the sum of the two before, both 0). Montana people: 444 (baseline minus 1).
* `--safe` again: 450 files, 0 created, 0 updated.
