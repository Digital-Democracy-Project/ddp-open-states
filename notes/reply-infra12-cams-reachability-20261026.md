# REPLY (INFRA-12): the EC2-broker host reaches the Mac's CAMS on :8000, WireGuard is fine, and this host has NO `CAMS_API_TOKEN` at all (read-only; prod agent, 2026-10-26 19:43 UTC)

Nothing was changed, restarted, triggered or deployed. The only request sent was the GET on `/api/v1/health`; no POST, no test alert. No secret was printed; I read variables by exact name and only the yes/no of whether they are set. This is the **EC2-broker host only**: I have no access to the EC2 civic host and could not check it.

## 1. Reachability: works
`curl -m 5 -sS http://10.0.0.8:8000/api/v1/health` from this host at 19:43:15 UTC: **HTTP 200 in 0.030 s**, body **`{"status":"ok","timestamp":"2026-10-26T19:43:15.289410+00:00"}`**. For comparison, the Mac's ddp-sync on `:8001` answered 200 in 0.056 s in the same minute. **The health endpoint answered without any credential** (I sent none). `ip route get 10.0.0.8` shows the route via `wg0` with source `10.0.0.11`.

## 2. WireGuard
Interface `wg0`, `Address = 10.0.0.11/32`, **one peer** with **`Endpoint = 172.31.81.51:51820`** and **`AllowedIPs = 10.0.0.0/24`** (so `10.0.0.8` is inside AllowedIPs; the kernel route `10.0.0.0/24 dev wg0 scope link` agrees). The tunnel is up: **latest handshake 106 s before I read it** (19:41:38 UTC). I read only the Address, Endpoint and AllowedIPs lines of `/etc/wireguard/wg0.conf` with `sudo` (the directory is root-only); no key line was printed, and the peer's public key was not shown. The peer is the hub at the Endpoint above; I did not check how the hub forwards to the Mac.

## 3. Token match: there is no token on this host to hash
**`CAMS_API_TOKEN` is not defined in any `.env` I checked** (`/opt/ddp-sync/.env`, `/opt/ddp-broker-py/.env`, `/opt/ddp-open-states/.env`, `/opt/ddp-open-states/deploy/.env`: 0 lines each; the api-v3 `.env` paths do not exist here) **and it is not set in any running container** (`ddp-sync-ddp-sync-1`, broker web and celery, `ddp-openstates-api-1`: all "not set"). So there is nothing to compare with the Mac's `6e4334cfc8dc`; I did not run the hash because there is no value to hash (the variable is **absent**, not blank). This is consistent with the code: `ddp_sync/config.py` reads `CAMS_API_TOKEN` with default `""`, and several ddp-sync routes answer "CAMS_API_TOKEN not configured on this instance" (`triggers.py` lines 1654 and 1682), and a code comment in `ingestion/sources/openstates.py` says a host with no CAMS access leaves `cams_api_token` unset. So **ddp-sync on this host cannot authenticate to CAMS today**, only reach its open health endpoint.

## 4. `render-env.sh`
**It maps neither `CAMS_API_TOKEN` nor any `CODEBOT_*` variable**: zero mentions of CAMS or CODEBOT in `infrastructure/render-env.sh`, in this host's copy (ddp-sync `74d72fe`) or on `origin/main` (`958d6b7`, fetched today). Its `KEY_MAP` (secret key name to env var name) lists DDP_SYNC, OPENAI, PINECONE, OPENSTATES, CONGRESS, BREVO, ZAPIER, WEBFLOW_*, SLACK_BOT_TOKEN, MAC_DDP_SYNC_API_KEY and RDS_OPENSTATES_API_KEY, nothing for CAMS. I did **not** open the `ddp-sync/credentials` secret to see whether it holds a CAMS key under another name.

## So, for the INFRA-12 decision
The network half is ready from this host (route, tunnel and port 8000 all work). The **auth half is not**: to let the EC2 senders try CAMS first, `CAMS_API_TOKEN` would have to be added to this host's environment (for example by adding it to the `ddp-sync/credentials` secret and to `render-env.sh`'s map) and then compared against `6e4334cfc8dc`. I changed none of that.

## Not checked
The EC2 civic host; the hub's forwarding to the Mac; whether `ddp-sync/credentials` has a CAMS entry; any CAMS endpoint other than the health GET. Ramon records the result on INFRA-12; I left the ticket alone.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
