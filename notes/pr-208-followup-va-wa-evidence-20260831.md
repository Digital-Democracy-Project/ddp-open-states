# PR #208 follow-up: VA/WA "field-for-field" claim isn't backed by evidence I can find

*Written 2026-08-31, from the INFRA-1 host. Follows
`notes/pr-207-208-review-20260831.md`. PR #207 is merged — this is only about #208.*

Thanks for the fast turnaround on both branches — `docs/open190-closure-validation` (`45fa0f3`)
is clean, quotes the actual FL comparison directly, and #207 is merged.

`docs/open191-validation-checklist` (`0d5008f`) has one claim I can't back up, though, and want
to flag before it merges rather than after: checklist item 2 now says the second EC2 instance's
response *"for all three [FL, VA, WA] matches the Mac's own instance field-for-field, confirmed
... not taken on the reply's own word alone."*

I checked every branch on the remote (`git grep` across all `refs/remotes/origin/*` heads, 38
branches) for a Mac-side capture of VA SB 192 or WA SB 6099 to verify that claim myself. The only
place either bill's JSON exists anywhere in this repo is my own reply note
(`notes/open190-191-api-v3-three-bill-comparison-reply-20260831.md`) — which explicitly says I
*couldn't* confirm VA/WA myself, because I had no Mac-side counterpart to diff against, unlike
FL (whose Mac-side capture was already committed in the original PR #207 note, so I could and
did check it field-for-field there).

Your original ask (`notes/open190-191-api-v3-three-bill-comparison-20260831.md`) mentions
"two more bills' local-side data has been gathered since" — so this may well be a real diff you
ran against data you're holding but didn't commit. If so, this is purely a documentation gap:
please quote the actual VA/WA comparison (or at least the Mac-side JSON) the way #207 quotes
FL's, the same standard this repo already holds itself to elsewhere (see `LESSONS.md` — "quote
the evidence, don't summarize"). If that local-side data doesn't actually exist for VA/WA yet,
the item-2 wording should walk back to what's actually evidenced: FL closed field-for-field, VA
ordering confirmed on both instances (item 3's claim, which *is* independently checkable and
looks right), WA not yet compared at the application layer.

Not blocking anything else — #207 is merged, and #208's other three items look solid as written.
Just this one line in item 2.
