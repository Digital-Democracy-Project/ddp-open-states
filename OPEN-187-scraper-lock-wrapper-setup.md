# OPEN-187: setup recipe for the shared scrape lock's Mac-side access

`scraper-memory.sh`'s new `scraper_memory_acquire_lock`/`scraper_memory_release_lock` functions
(and `cloud_collector.py`'s `SourceLock`, already live in Fargate) need a shared S3 object both
sides can read and write with **conditional writes** (`IfNoneMatch`/`IfMatch`) — that's what makes
acquiring the lock atomic, no separate coordination service needed.

The Fargate side already has this: `ddp-scraper-task-role`'s existing `s3:PutObject`/`GetObject`
grant on `ddp-openstates-scraper-memory` covers conditional writes for free (they're request
headers, not a separate IAM action). **The Mac side has none at all** — this repo's existing
`ddp-prod-s3-openstates-backups` wrapper only reaches the *other* bucket
(`ddp-openstates-backups`), and its `put`/`get`/`ls`/`info` contract has no conditional-write
support to begin with.

This is an operator action (root/sudo), not something this environment can do for itself —
matching how `ddp-prod-s3-openstates-backups` itself was set up (`ddp-infra/PLAN-bill-document-provenance.md`,
2026-07-25: real credentials live in a root-owned proxy, exposed to `agentsmith` only through a
narrow, sudo-gated wrapper).

## 1. IAM: a scoped credential for `ddp-openstates-scraper-memory`

Same shape as the task role's own policy (`infra/fargate-spike/README.md`), minus `s3:ListBucket`
(the lock and memory keys are always addressed directly, never listed by this wrapper) and with
`s3:DeleteObject` deliberately **absent** — `SourceLock`/`scraper_memory_release_lock` never
delete; releasing means writing an already-expired lock body, so this credential never needs
delete permission at all:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ScraperMemoryAndLockReadWrite",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": ["arn:aws:s3:::ddp-openstates-scraper-memory/*"]
    }
  ]
}
```

## 2. Root-owned proxy: `/usr/local/ddp-db-proxy/s3-scraper-memory.sh`

Mirrors `s3-openstates-backups.sh`'s own shape (put/get/ls/info), plus three lock-specific
subcommands that do the actual conditional-write work. Embed the scoped credential from step 1
here, root-owned, mode `700`:

```bash
#!/usr/bin/env bash
# Root-owned. Holds a credential scoped to ddp-openstates-scraper-memory only (see OPEN-187's
# setup doc in ddp-open-states-dev for the exact policy). Never exposed directly to agentsmith --
# reached only via the sudo-gated wrapper below.
set -euo pipefail
export AWS_ACCESS_KEY_ID="<fill in>"
export AWS_SECRET_ACCESS_KEY="<fill in>"
export AWS_DEFAULT_REGION="us-east-1"
BUCKET="ddp-openstates-scraper-memory"

case "$1" in
    put)      exec aws s3 cp "$2" "s3://$BUCKET/$3" --only-show-errors ;;
    get)      exec aws s3 cp "s3://$BUCKET/$2" "$3" --only-show-errors ;;
    ls)       exec aws s3 ls "s3://$BUCKET/${2:-}" ;;
    info)     exec aws s3api head-object --bucket "$BUCKET" --key "$2" ;;

    # --- lock-specific: conditional writes, the reason this wrapper exists at all ---

    # lock-acquire <key> <body-file>  -- conditional PUT, fails if the key already exists.
    # Prints the new ETag on success (stdout), nothing on failure (relies on aws's own exit
    # code + stderr, which scraper-memory.sh matches by text as it already does for get/ls).
    lock-acquire)
        aws s3api put-object --bucket "$BUCKET" --key "$2" --body "$3" \
            --if-none-match '*' --query ETag --output text
        ;;

    # lock-read <key>  -- prints "<etag>\t<body-as-one-line>" on stdout. Fails like `get` on a
    # missing key (same (404)/NoSuchKey shape scraper-memory.sh already matches on).
    lock-read)
        etag=$(aws s3api head-object --bucket "$BUCKET" --key "$2" --query ETag --output text)
        body=$(aws s3 cp "s3://$BUCKET/$2" - --only-show-errors)
        printf '%s\t%s\n' "$etag" "$body"
        ;;

    # lock-reclaim <key> <body-file> <expected-etag>  -- conditional PUT, fails if the key's
    # current ETag no longer matches (someone else reclaimed or refreshed it first).
    lock-reclaim)
        aws s3api put-object --bucket "$BUCKET" --key "$2" --body "$3" \
            --if-match "$4" --query ETag --output text
        ;;

    *) echo "usage: $0 {put|get|ls|info|lock-acquire|lock-read|lock-reclaim} ..." >&2; exit 2 ;;
esac
```

## 3. User-facing wrapper: `~/bin/ddp-prod-s3-scraper-memory`

Same shape as `~/bin/ddp-prod-s3-openstates-backups`, just naming the new proxy and passing
subcommands straight through (the lock ones take a variable number of args, so this is a thinner
passthrough than the original rather than one `case` arm per command):

```bash
#!/bin/bash
set -euo pipefail

usage() {
  echo "Usage:" >&2
  echo "  ddp-prod-s3-scraper-memory put <local-file> <object-key>" >&2
  echo "  ddp-prod-s3-scraper-memory get <object-key> <local-file>" >&2
  echo "  ddp-prod-s3-scraper-memory ls [prefix]" >&2
  echo "  ddp-prod-s3-scraper-memory info <object-key>" >&2
  echo "  ddp-prod-s3-scraper-memory lock-acquire <object-key> <body-file>" >&2
  echo "  ddp-prod-s3-scraper-memory lock-read <object-key>" >&2
  echo "  ddp-prod-s3-scraper-memory lock-reclaim <object-key> <body-file> <expected-etag>" >&2
  exit 2
}

[ $# -ge 1 ] || usage
exec sudo /usr/local/ddp-db-proxy/s3-scraper-memory.sh "$@"
```

`chmod 755 ~/bin/ddp-prod-s3-scraper-memory`, and a `sudoers.d` entry allowlisting exactly this
one script for `agentsmith`, matching the existing `ddp-prod-s3-openstates-backups` entry's shape.

## 4. Point `scraper-memory.sh` at it

Nothing to do here — `SCRAPER_LOCK_S3_CMD` already defaults to `ddp-prod-s3-scraper-memory`
(this PR). Once steps 1–3 are done, `command -v ddp-prod-s3-scraper-memory` resolves and
`scraper_memory_acquire_lock`'s config check (mirroring `scraper_memory_check_config`'s existing
one) passes.

## What this deliberately does not do

**Does not touch `ddp-prod-s3-openstates-backups` or its proxy at all.** That wrapper keeps
serving `ddp-openstates-backups` (Postgres dumps under `db/`) exactly as it does today — this is
a wholly separate credential and a wholly separate bucket, on purpose, for the same reason
`ddp-openstates-scraper-memory` exists as its own bucket rather than a prefix (OPEN-200/OPEN-183:
mixing lifecycle policies on one bucket is what caused the 30-day-deletion discovery this session).
