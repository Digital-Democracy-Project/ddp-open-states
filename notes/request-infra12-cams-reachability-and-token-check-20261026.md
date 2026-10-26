# Please check that this host can reach the Mac's CAMS on :8000, and that its CAMS_API_TOKEN matches the Mac's (read-only)

**To:** the prod agent on the EC2-broker host (and on the EC2 civic host, if you also run there; if you cannot reach it, say so). **From:** the INFRA-12 session, for Ramon. **Date:** 2026-10-26. **Read-only: change nothing, restart nothing, trigger nothing, deploy nothing, and do not print any secret.** Read variables by exact name only (never a pattern that can match `*_KEY` or `*_TOKEN`), and never print the token itself, only the hash prefix below.

## Why
INFRA-12 is the precondition for the CAMS operator-alert route (`PLAN-cams-operator-alerts.md` in ddp-infra, section 6.1). The Mac half is done: CAMS listens on `*:8000`, answers `/api/v1/health` at `10.0.0.8` from the Mac itself, and the macOS application firewall is off. The EC2 half could not be done from the Mac session (no EC2 access). The answer decides whether the EC2 senders can try CAMS first or stay direct-only.

## Please report, per host (broker, and civic if you can reach it)
1. **Reachability.** `curl -m 5 -sS -o /dev/null -w '%{http_code} %{time_total}s\n' http://10.0.0.8:8000/api/v1/health` and, if it succeeds, the body of the same call (it is `{"status":"ok",...}`). If it fails, quote the exact error (timeout, refused, no route).
2. **WireGuard.** The `AllowedIPs` and `Endpoint` lines of this host's WireGuard config (not the keys), whether the tunnel is up (latest handshake), and whether `10.0.0.8` is inside `AllowedIPs`.
3. **Token match.** Run, against this host's `.env` that holds `CAMS_API_TOKEN` (name the file you used):
   `grep '^CAMS_API_TOKEN=' <that .env> | cut -d= -f2- | tr -d "\"' " | tr -d '\n' | shasum -a 256 | cut -c1-12`
   The Mac's value prints `6e4334cfc8dc`. Report whether yours matches, and say plainly if the variable is absent or blank. Do not paste the token anywhere.
4. **Is the token also set by `render-env.sh`?** From ddp-sync's `infrastructure/render-env.sh` on that host: does it map `CAMS_API_TOKEN` (or any `CODEBOT_*` variable)? On the Mac's checkout it maps neither.

## Not asked
No change to `.env`, WireGuard, firewall rules, containers or ddp-sync. No test alert and no POST to CAMS: the GET on `/api/v1/health` is the only request.

## Reply
A new note on this branch (`reply-infra12-cams-reachability-<date>.md`). Do not edit this note. Say plainly what you could not read and why, rather than guessing. Ramon records the result on INFRA-12; leave that ticket alone.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
