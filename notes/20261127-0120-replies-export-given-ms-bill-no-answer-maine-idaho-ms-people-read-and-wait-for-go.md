# Replies 11-27 01:20 UTC: the OR/WY export, the Mississippi `bill_no` answer, and where the four requests stand

## OR/WY LegBot export (`7d4119e4`): done, read-only; file to Ramon in session, not in this note
* **Export given to Ramon in session**: a private text file on the EC2 host, `legbot-export-or-wy-20261127.txt` in my ops folder (mode 600; 30 bills, 115 artifact blocks of the four types, plain text). Nothing was written to production and no artifact was regenerated.
* **Sampling rule:** for each state, the 100-bill sample sorted by bill number; **every 7th bill (positions 7, 14, ... 84: 12 bills)**, plus **the longest bill not already in it** (Oregon HB 4070, 145,148 characters; Wyoming SF 65, 89,801; the only Wyoming bill over 50,000), plus **the first two bills in sorted order that had a failed artifact** and were not already in. 15 bills each. I did **not** balance enacted against died-in-committee or one-version against multi-version bills; the every-7th rule is stable but not stratified.
* Each block: state, session, bill, longest source document, then every `bill_summary`, `bill_changelog`, `bill_pros_cons` and `bill_impact_analysis` artifact with status, version note, `model_name`, `origin` and the text; a failed artifact shows its failure reason (4 such blocks, all `insufficient_information`).

## Mississippi (`8d2a2e23`): the `bill_no` question answered; nothing started
* **Yes, a ddp-sync trigger can pass `bill_no` on the Fargate path:** `POST /ddp-sync/v1/trigger/openstates-scrape/ms?sessions=2026 bill_no=SB2838,2026 bill_no=HB515,2026 bill_no=HB1330,2026 bill_no=HB1924` (each entry is a session code then `key=value`; its parser names `bill_no=HB1` as a working example). Four collections, one per entry; the pipeline then archives and (for a live state) triggers LegBot only if `legbot_replica` is on (it is off for Mississippi). Whether to add `full=true` is yours: it removes the `start=` cutoff, and I do not know if `bill_no` alone already ignores it. **The exact bill-number spelling Mississippi's collector expects (`SB2838` or `SB 2838`) I have not checked.**
* **Preview:** `cloud_collector.py` has no preview or dry mode that I could find (no flag with that meaning). A preview would have to be your own run on the Mac; I can run the four for real only on Ramon's go, and I can read the stored vote counts per bill beforehand if you want a before-number.
* Part 1 (the people load, `os-people to-database ms`, with `--safe` first as I did for Montana) and Part 2 each wait for Ramon's go in this session.

## Maine go-live (`8ed38a95`): #501 is merged; waits for Ramon's go
* `origin/main` of ddp-open-states is now `af88d018` (the #501 merge); my production checkout is at `333c2768`. I have not pulled, run the dry run or rolled out anything.

## Idaho (`a9d0c34a`): waits for Ramon's go; one thing I can confirm
* The refresh-extraction dry run runs in the ddp-sync container with the core `647bb399` (live there; drift check exit 0); I ran this tool the same way for other states. I will print the exact lines and the commit, and commit nothing, when Ramon gives the go.
