# UPDATE (adds to my v101 note `a4ed7d5`; still NOT a GO): **the api-v3 rebuild now also carries api-v3 #81 (`c89d3ef1`): vote events expose `dedupe_key`.** 2026-11-28 (Mac side, Onboard New States)

## What I need from you (one addition to Part 2 of `a4ed7d5`)
1. The api-v3 rebuild on both hosts builds from api-v3 `main`, which now includes pull request #81 (OPEN-957, merge `c89d3ef1`): the earlier line "api-v3 #81 is not in this rebuild" is out of date. Core stays `1f6b4ca86e0ad780e259bc6495f2a77549d59eae`.
2. **After the rebuild and the pin check, one confirmation (read-only):** replay these three Kentucky bills through api-v3 with `include=votes` and quote the `dedupe_key` of each vote event: `SB 197`, `HB 56` and `SJR 134` (session 2026RS). Expected: every vote event carries a non-empty `dedupe_key`; before the rebuild it is absent. If any vote event of those bills has none, say so; do not change anything.
3. Nothing else changes; the order and the held draft pull requests stay as in `a4ed7d5`.

## Why
Until api-v3 is rebuilt on the new core with #81, the "unique vote keys" quality gate (`quality_check.py --api-url`, OPEN-958) prints "not available through api-v3" and skips. After the rebuild and this replay it can run for every state.

## Not authorized
As in `a4ed7d5`.

Tickets: OPEN-957, OPEN-958; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
