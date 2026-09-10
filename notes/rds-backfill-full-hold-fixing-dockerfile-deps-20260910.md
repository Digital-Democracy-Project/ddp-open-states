# RDS backfill: hold everything, not just wa/us -- fixing the outdated-package problem first

*Replies to `notes/ut-discrepancy-root-caused-hold-wa-us-20260910.md`.* Ramon's call: **hold all
remaining RDS backfill work** -- `fl`, `va`, `wa`, `us`, everything past `ut` -- not just the two
`refresh-extraction` jurisdictions I'd flagged. `mi` and `ut` are already committed and stay as
they are; nothing further until the underlying package-freshness problem is actually fixed, not
just documented.

## Why the wider hold, beyond what I'd flagged

Even though `fl`/`va` only run `recompute-diff-order` (no re-extraction step), that command still
computes diffs from whatever `raw_text` is *already stored* -- and some of that stored text was
itself originally extracted by this same aging toolchain at some point. Rather than reason
case-by-case about which jurisdictions are "safe enough," simplest and most conservative is: stop
everything until the tool itself is current.

## What's happening on this end

Not just poppler in isolation -- the same root cause (the container's base image freezes
OS-level package versions at whatever the base Debian release shipped in 2021, while this Mac's
own tooling tracks current releases) applies to every package installed the same way in that
Dockerfile. Working through a proper fix for that now, with the same care as everything else
today -- this touches the identical file OPEN-263's earlier regression came from, so it's getting
a deliberate look and independent review before anything gets rebuilt and redeployed, not a rushed
patch.

Will report back here once there's something concrete to test and deploy. No action needed on
your end until then beyond sitting tight on the backfill.
