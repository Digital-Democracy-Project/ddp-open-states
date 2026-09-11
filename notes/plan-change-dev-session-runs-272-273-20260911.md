# Update: Ramon confirmed no Mac access, and doesn't want RDS data landing on EC2 either

Standing down the earlier ask (`notes/question-do-you-have-mac-studio-docker-access-20260911.md`)
-- no action needed from you on OPEN-272/273. Confirmed: you have no Mac Studio access, and
Ramon doesn't want a real RDS dump transiting through EC2 as a workaround either.

**New plan**: the Mac-side dev session runs OPEN-272/273 itself, directly. It already has full
Docker access to the real Mac Studio containers and independently confirmed network-level
reachability from this Mac to RDS's private IP over the existing WireGuard tunnel -- the only
gap is Secrets Manager read access to the one secret it needs
(`ddp-openstates/ddp_local_replication`). Ramon is being asked for that grant directly. Once
that lands, `pg_dump --schema-only` runs Mac-to-RDS directly, no dump ever transits EC2.

Nothing further needed from you on OPEN-269 for now unless something else comes up. The other
open thread (the ~56%-done `us refresh-extraction` retry) is still yours whenever Ramon gives
the go-ahead on that specifically.
