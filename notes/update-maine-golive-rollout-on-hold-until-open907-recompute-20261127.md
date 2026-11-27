# UPDATE (HOLD; supersedes the timing of `request-golive-maine-…-pr501-…`, 8ed38a9): **do NOT roll out Maine's go-live (#501) yet.** 2026-11-27 (Mac side, Onboard New States)

**What I need from you: nothing now. Please do not run the Maine manifest rollout until I post a note that lifts this hold.**

Ramon decided today (recorded on OPEN-907, comment `23862`; via the PM): **"Wait for the fix."** Maine's go-live (#501, merged `af88d018`) waits until:
1. openstates-core **#179** (OPEN-907: Maine's amendment papers become non-versions) is merged and carried in a scrapers image, and
2. `os-text-extract recompute-diff-order me` has been run: **dry run first** (expect not_a_version 1,792, 820 comparisons re-based, 1,792 nulled; the builder's expectation, not a run), and **the commit on Ramon's own go note**.

Why: going live turns on search refresh and embedding, which read the stored versions; today 1,792 amendment papers are stored as bill versions (my replica count) and 524 bills' latest version would change after the fix. Open for Ramon: a not-enacted bill's only real version becomes its Introduced text.

Everything else in `request-golive-maine-…` (steps, checks, not-authorized list) stands for when the hold is lifted.

Tickets: OPEN-672 (ME), OPEN-907; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
