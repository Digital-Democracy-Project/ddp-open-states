# OPEN-280: please drop profiles_profile from the publication -- crash-looping on a real conflict

47 of 48 tables synced clean after the full-schema refresh. The 48th, `profiles_profile`, is
crash-looping (confirmed in the local Postgres log, retrying every ~5s):

```
ERROR:  duplicate key value violates unique constraint "profiles_profile_pkey"
CONTEXT:  COPY profiles_profile, line 1
```

Real cause: the Mac's `profiles_profile` already has a real row (the original one-time
snapshot, api-v3's own local API-key auth data) -- logical replication's initial COPY doesn't
truncate the target first, so it collides with that existing row every time it retries.

**Decided (Ramon, via me): drop this table from ongoing replication, don't overwrite the Mac's
copy.** `profiles_profile` backs api-v3's own API-key auth, which is legitimately per-host, not
shared state -- each api-v3 instance (Mac's, EC2's) manages its own consumers' keys. Letting it
sync would mean any future RDS-side change to this table silently propagates here and could
swap out or wipe whatever key currently authenticates real requests to this Mac's api-v3, with
no warning. Unlike the actual bill/vote/person schema (where RDS genuinely is the single source
of truth), this one table doesn't fit the "replicate everything" model, and it wasn't part of
the original design's intent either -- always documented as a one-time snapshot, not an
ongoing-sync target.

**What I need from you**: `ALTER PUBLICATION ddp_legbot_publication DROP TABLE
public.profiles_profile;` on the RDS side. Once that's done, I'll refresh the subscription
here, which should cleanly stop tracking it (no data loss on the Mac's side either way -- its
existing row stays exactly as it is, this whole exchange is only about whether it's part of
*ongoing* sync going forward).

Everything else (all 47 real OpenStates/pupa tables) is done, verified, `srsubstate='r'`. This
is the only remaining loose end for OPEN-280.
