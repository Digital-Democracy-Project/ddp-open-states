# CHECKPOINT (prod agent): Alabama go-live manifest rollout done on EC2 (ddp-open-states `4c78d958`). 2026-11-27 21:35 UTC (production host)

Ramon's go in my session ("Alabama go-live rollout (#513)").
* **Gate and dry run:** `origin/main` was `4c78d958`, contains #513. Dry run exit 0. **The pull also brought more than Alabama**, which I put to Ramon before the real run (he said yes): `legbot_send_abstract` added for every state and set **true for Oregon only** (OPEN-929; nothing on EC2 reads it: no such code in this host's ddp-sync), and North Dakota `diff_cleaner: clean_nd_text` (#511). No other state changed.
* **Real run:** exit 0. Revision `9d447ae56` to `4c78d9582`. md5 of the checkout file, api-v3 copy and the file in the container all `172f5c8c...` (equal); api-v3 healthy, no restart; drift check exit 0 (repo lists, and with ddp-sync's lists); core pin check OK (`1e138376` on all three); `/schedule` still 35 jobs; no ddp-sync restart; ddp-sync's own read: Alabama `status live`, embedding, search refresh, smoke and QA all True, `replica_routing` True, `legbot_replica` False.
* **Not done:** the Mac host's manifest copy is Ramon's step; `legbot_replica` and VoteBot's state list untouched. Alabama's first embedding and search-refresh pass runs inside ddp-sync's process; I will report when it finishes and the smoke and QA results. I will use the narrow restart rule meanwhile.
* **Nevada:** dry run answered in `177570be6`; commit held.
* **Virginia (open question for you):** `fae09ff4f` reports 6 fewer vote events than your 11,553 (2026 = 11,512, 2026S1 = 35) and I could not find your 38 "Agree to R" votes by text. Ramon wants this confirmed with you before the broker release: **please tell me whether the 6 are expected** (for example a count that differs between the replica and production) **or something to investigate.**

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
