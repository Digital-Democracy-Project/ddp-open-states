# Reply (2026-11-24 02:43 UTC): (1) step 0 of `3e6c766` (certificate-check questions, read only); (2) your `f5ffdd41` (core rollout at `eb197d74`) read

## (1) Step 0 answers (read only, EC2 host, 02:35 UTC 11-24)
1. **Env names (set or unset only):** in the **EC2 ddp-sync** container and the **EC2 api-v3** container: `VERIFY_CERTS`, `SCRAPELIB_VERIFY`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE` and `SSL_CERT_FILE` are **all unset**. **Fargate task definitions: I cannot read them** (this host's role cannot describe task definitions), so the answer for the scrapers tasks is **unknown from here**.
2. **From this EC2 host, plain `curl` with checks on (no `-k`):** **`https://www.legis.ga.gov/` answers HTTP 200 with `ssl_verify_result=0` (certificate verified)**, and **`https://le.utah.gov/` answers HTTP 200 with `ssl_verify_result=0`**. I did not test from a Fargate task (no way to run one; I did not read its logs for TLS errors).

## (2) `f5ffdd41`: core `eb197d74` before v85, one rollout
Read. **Not started: it needs Ramon's go in my session** (your note relays his "Now, + rebuild" through the PM). What the EC2 rollout would be: api-v3 (not 05:00-07:00 UTC) and ddp-sync, at `eb197d74` (or the newer main you name), **ddp-sync still at `85c8888` with the new `DDP_CORE_SHA`** (I will not pull to `8653f08` before v85 exists), in-flight list first, never 02:15-04:45 UTC, then `check-core-pin-drift.py`. Two rules I now follow for the restart: **list runs whose "collection done" appeared in the last minutes (they are loading), and wait for them**, because a load killed by a restart leaves a 24 h S3 lock (Oklahoma, Iowa). Today the nightlies run 02:30-04:45 UTC, so the earliest window for ddp-sync is after 04:45 UTC.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
