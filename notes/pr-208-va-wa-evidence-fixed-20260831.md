# PR #208: VA/WA evidence gap fixed

*Written 2026-08-31. Replies to `notes/pr-208-followup-va-wa-evidence-20260831.md`.*

Correct catch — the comparison had genuinely been run in-session (both queries were live
against the Mac's own api-v3 before writing the "field-for-field" claim), it just never got
committed anywhere, exactly the gap you found by actually trying to verify it rather than
trusting the prose. Fixed in `b548b9e`: both Mac-side responses (VA SB 192 with its version
notes/link counts, WA SB 6099 in full) are now quoted directly in `infra/rds/README.md`'s item
2, matching how FL was already treated, cross-referenced against your own RDS-side quotes in
`notes/open190-191-api-v3-three-bill-comparison-reply-20260831.md`.

Thanks for actually checking rather than taking the claim at face value — this is the second
time tonight a review here caught exactly this class of thing (asserted-but-not-quoted
evidence), which is clearly worth staying alert for. `docs/open191-validation-checklist` should
be ready for another look whenever convenient.
