# Ramon: proceed with OPEN-272 and OPEN-273's real execution -- he's stepping away

Ramon authorized this before going away from his desk, so use this note as standing
authorization for the rest of this thread rather than waiting for a live reply.

## Proceed with both, in order

**OPEN-272** (`rebuild-local-replica.sh`): take a real `pg_dump --schema-only` of the 7 tables
from RDS now that `ddp_local_replication` exists and the publication is live, and run it for
real (build the new local database ALONGSIDE the existing `openstates` database -- the script
is explicitly non-destructive, doesn't touch or repoint anything existing). Report the real
output (all 7 tables present/queryable, the stripped `opencivicdata_division` FK confirmed
absent, the api-v3 container-startup check) via `notes/`.

**OPEN-273** (`setup-subscription-and-readonly-role.sh`): once 272's new database exists for
real, stand up the real `CREATE SUBSCRIPTION` against RDS (using `ddp_local_replication`'s
real credential) and the real `ddp_local_readonly` role. Report initial-sync completion (all 7
tables reaching `srsubstate='r'`, matched by name not just count), the real read-access check,
and both write-refusal checks (session-default and post-`SET TRANSACTION READ WRITE`).

Do NOT repoint the real `ddp-openstates-api-1` container or touch the existing `openstates`
database at any point in either step -- both scripts are designed not to, by design; keep it
that way.

## On small IAM/environment gaps if one comes up

Ramon's explicit answer: **narrowly self-resolve a clearly small, same-spirit gap (another
Describe/Get-type permission, a missing CA bundle, an old-CLI workaround, etc. -- the same kind
of thing that came up during OPEN-271) and report it here afterward**, rather than blocking on
his live sign-off. This does NOT extend to anything broader (e.g. wider IAM scope than
strictly needed for these two scripts, anything destructive, anything touching the real
`openstates` database or `ddp-openstates-api-1` container) -- those still need his explicit
sign-off same as before, and he won't be reachable live right now, so hold on anything in that
category until he's back.

## Once both land

Report real completion for both here, same as OPEN-271's own writeup, so tickets can be closed
out against real evidence. OPEN-274 (health check + rebuild drill) and OPEN-275 (freshness
check, currently feature-flagged off) become real-execution candidates too once a real
subscription actually exists to check the health of.
