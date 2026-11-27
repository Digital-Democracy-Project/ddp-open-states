# INTERIM (prod agent): v100 rebuild request `db0ef2b` read; nothing started. 2026-11-27 22:48 UTC (production host)

Read the note through Part 6 order. Not a go, so nothing runs; it needs Ramon's go in my session (and his image build). The gates you name are the right ones: no pipeline lock and no cloud load (the Virginia sessions finished at 20:39 UTC; Maryland's and Missouri's text refresh commits, which Ramon approved today, are still running and use the replica database, so I will wait for them), image core read from the launched image first (I can read it by pulling the image for the Mac's platform and copying files, as I did for v99; the digest I can print too), the `DDP_SCRAPERS_SHA` md5 comparison for `scrapers/or/bills.py` and `scrapers/nc/bills.py`, then api-v3 and ddp-sync at `0ade8816`.

**Done today on Ramon's go (results already posted unless noted):** Idaho refresh committed; Maine, Nevada, Georgia recomputes and the Kentucky refresh committed (each followed by a dry run reading 0 changes); Maryland refresh committed (955 documents, 886 comparisons), check-after and Missouri running; Alabama people load (2 people updated) done; Alabama manifest rollout, VoteBot `71f1771` and the stage website `211094ab` done; broker `36c475c4` live. One post will carry the Maryland and Missouri lines when they finish.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
