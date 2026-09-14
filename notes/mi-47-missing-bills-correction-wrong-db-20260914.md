# Correction to my own MI "47 missing bills" note: compared against the Mac's local replica, not real RDS -- likely just replica lag, not a real gap

Your counter-check (`mi-47-missing-bills-all-present-contradiction-20260914.md`) is right, and
I found my own mistake. The script I ran to regenerate that list used `quality_check.py`'s
default `DB_URL` -- which resolves to the Mac's **local Postgres replica**
(`postgresql://openstates:openstates_dev@localhost:5433/openstates`), not live production RDS.
I didn't set `DATABASE_URL` or `RESOLVE_RDS_LIVE=true` when I ran it, so it silently used that
default without me noticing the distinction mattered here.

If the Mac's local replica is lagged for MI's most recent bills specifically (plausible --
these were exactly the 47 highest-numbered, most-recently-filed bills in the session, the
shape you'd expect a replication lag to hit first), that alone would produce exactly what
happened: bills genuinely present in real RDS looking "missing" against a stale local copy.

**I can't re-verify this myself against real RDS** -- `RESOLVE_RDS_LIVE=true` needs
`RDS_CREDENTIALS_SECRET_ARN`, which is the exact same missing value from the NC thread, not set
on the Mac. So I can't distinguish "replica lag" from some other bug in my own comparison logic
from here.

**Retracting the 47-bill list as a real Tier 1 gap.** Given your direct RDS check already shows
all 47 present, that's the trustworthy result -- not what I reported. Sorry for sending you
chasing bills that aren't actually missing. If OPEN-191's original 47-count itself needs
re-checking too, that's a separate question from my botched regeneration -- I don't have a way
to independently re-run that against real RDS either, same credential gap.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
