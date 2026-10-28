# HOLD: do not run the api-v3 OPEN-398 deploy yet (request `0dbe72a`); ddp-sync pull and restart are NOT on hold

2026-10-28 (just after 00:40 UTC). Ramon asked me to investigate OPEN-398 further before it goes to production. **Please do not do any step of `0dbe72a` (the api-v3 `03fbb34` pull, rebuild, recreate) until a later note from me says to.** If you have already started, stop after the step you are on, change nothing further, and report what is done (the before-timing measurement alone is harmless and still welcome if it is already done).

**Not affected:** the ddp-sync pull and restart in `e2a18fa` and its amendment `c4d61fb` (PR #251 is merged) stand; the api-v3 deploy and the ddp-sync restart are independent.

Reason, so you know it is not a fault on your side: on the Mac the change gave less speed-up than the PR claimed, and the first 20 results for very common words changed almost entirely. I am checking whether the change is worth shipping as written.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
