# OPEN-271 fully done -- real setup complete, real read/write verification confirmed

Ran the full sequence against real production RDS, post-reboot.

## 00-generate-role-secret.sh

This host's AWS CLI (v1.19.1 / old botocore) doesn't expose `--generate-secret-string` as a
`create-secret` flag at all (`Unknown parameter in input: "GenerateSecretString"` even via
`--cli-input-json` -- a real version gap, not a syntax mistake). Worked around it while
preserving the same security property (password never touches my own shell output/history):
used the separate `secretsmanager:GetRandomPassword` action to generate the password
server-side, captured it directly into a shell variable inside one self-contained script, and
piped it straight into `create-secret --secret-string`, never echoing it -- same pattern
`02-setup.sh`/`03-verify-role-can-read.sh` already use for *reading* a secret, just applied to
the *create* side. Needed one additional IAM grant (`secretsmanager:GetRandomPassword`,
`Resource: "*"` since it's not tied to any specific secret) -- Ramon granted it. Secret created
successfully (`ddp-openstates/ddp_local_replication`), only ARN/Name/VersionId ever printed.

## 01-inspect.sql (fresh, post-reboot)

All clean, matches the pre-reboot run except the two that mattered:
`wal_level=logical`, `rds.logical_replication=on` (both now correct). Slots/senders: 20/35
configured, 0/0 in use. All 7 tables present. All 7 already have valid REPLICA IDENTITY (real
primary keys) -- **zero remediation needed**, confirming the earlier prediction.
`openstates_admin` owns and can `SELECT` all 7.

## 02-setup.sh -- succeeded, real DDL committed

Hit two more real environment gaps along the way, both fixed properly rather than routed
around: (1) `sslmode=verify-full` needs a local RDS CA bundle -- downloaded the real one from
`https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem` to `~/.postgresql/root.crt`
(a public AWS truststore URL, not a secret); (2) the `RDS_DATABASE_URL` in this host's `.env`
has a percent-encoded password component that `urlparse().password` doesn't auto-decode --
needed `urllib.parse.unquote()` to extract the real value.

Output:
```
BEGIN / SET / CREATE ROLE / GRANT ROLE / GRANT / GRANT / GRANT / CREATE PUBLICATION / COMMIT
Publication tables (expect exactly the 7 above, nothing more, nothing less):
 public | ddp_bill_version_document
 public | opencivicdata_bill
 public | opencivicdata_billversion
 public | opencivicdata_billversionlink
 public | opencivicdata_jurisdiction
 public | opencivicdata_legislativesession
 public | opencivicdata_organization
(7 rows)
Expect true (replication role membership, NOT rolreplication):
 pg_has_role
-------------
 t
(1 row)
```
Exactly the 7 expected tables, nothing more. Membership check `t`.

## 03-verify-role-can-read.sh -- real read confirmed, write-refusal script bug hit (and independently confirmed as PR #240's already-known fix)

Read check: real counts on all 7 tables (`bill=73545 legislativesession=194
jurisdiction=343 organization=534 billversion=108625 billversionlink=193784
bill_version_document=193259`) -- role genuinely connects and reads.

Write-refusal check reported **FAIL** -- but did NOT take that at face value. Reproduced the
exact same INSERT directly and got `ERROR: permission denied for table opencivicdata_bill` --
the write **is** correctly refused. Traced the script's own false negative precisely: with
`set -o pipefail` active, `psql`'s own non-zero exit (expected here, from the SQL error)
becomes the reported pipeline exit status even when `grep -q "permission denied"` finds the
match -- pipefail reports the rightmost *failing* command (psql), not grep's own success.
Then found this is **already fixed, word-for-word the same root cause**, in your own
not-yet-merged PR #240 (captures output to a variable first, greps the variable). Didn't
merge it myself -- OPEN-269/271 is outside the scraper/archiver scope I'm authorized to
self-merge, leaving that decision to Ramon.

## Bottom line

**OPEN-271's actual RDS-side setup is complete and correct** -- role, grants, publication,
read access, and write-refusal all verified for real, independent of the one cosmetic bug in
the verification script itself (already fixed, pending merge). OPEN-272/273 should be
unblocked to run against this real schema now.
