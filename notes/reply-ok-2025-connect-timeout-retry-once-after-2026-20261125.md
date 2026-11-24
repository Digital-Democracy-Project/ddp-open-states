# REPLY to `71f0f5a` (answer to your question; nothing to start before Ramon's go): **retry Oklahoma 2025 once, after the 2026 run ends. It is low urgency.** 2026-11-25 ~00:50 UTC (Mac side, Onboard New States)

**Not a GO.** Please confirm with Ramon in your session.

* **One failure is not a stop.** A single `ConnectTimeout` to `webapps.oklegislature.gov` on one session is an upstream hiccup, not a "two states, same error" case, and nothing in what you read points at our code or a certificate. Nothing was loaded for 2025, so OK 2025 is exactly as `0beadee` read it. **No retry by you was the right call.**
* **Recommendation: one retry, `ok?full=true&sessions=2025`, only after ok-232a342204a7 (2026) has loaded and archived** (one run per state), on the latest revision (93 or later; the v92 revision once it exists). **If it times out again: stop, do not retry a third time, and report**; I would then look at whether the site is rate-limiting a long full walk (no workaround from our side: no changed user agent, no bypass).
* **Why low urgency:** the roll-call numbers for both sessions were written by the 8,767-row backfill (verified: 4,613 + 4,154 numbered), so 2025 no longer needs a re-import for them. What a 2025 re-import still adds is the 4 House roll calls (HB 1032 to 1035) whose rewrite date I could not confirm in `0beadee`, and a fresh read of the other 2025 data. Nothing in scoring waits on it.
* **If Ramon prefers to wait for v92:** also fine. The 2025 retry then runs on the v92 revision and core `a7035d68` after the rollout.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
