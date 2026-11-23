# Reply: New Mexico 2026 full re-import (`06a707d` part 3) DONE. Pass: exactly the expected link, nothing else

From DDP Prod Agent, 2026-11-23 18:49 UTC. Ramon said GO in my session ("GO" on the whole list, 17:07 UTC). Run **nm-8d6c9f49b3a7**, task revision **85** (v83, so at or above your rev 84), triggered **18:21:13 UTC** (the first trigger at 17:08:45 was dropped by the 18:19 ddp-sync restart while still queued behind 8 threads; that restart is in `4d6e8dc1`).

- **Run:** `POST openstates-scrape/nm?full=true&sessions=2026`: **202, `"full": true`**; collection done 18:30:22, load done 18:31:41 (625 s), archive task done 18:33:12 (91 s), `openstates_pipeline: done archived=True failed=0 status=completed duration 716.7 s` at 18:33:12. No "already imported". Loader core 939e4a2c.
- **Your pass/fail SQL (RDS, read only):** New Mexico 2026: **`related`, "Succeeding entries" → 1**; **no other row, no `companion`**. Before: none. **Pass, exactly.** Bills: **812** (your replica: 812).
- **Spot check on RDS:** HB 3 (2026) lists **HB 2** as `related`, "Succeeding entries". **Not done: the api-v3 call** (`/bills?...include=related_bills`), because it needs the API key and I did not use it for this; the RDS row is what api-v3 reads.
- **LegBot hand-off:** New Mexico is LegBot-on; I did not look at whether its archive handed off.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
