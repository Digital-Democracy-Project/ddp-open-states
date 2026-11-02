# Request (read-only): prove where the production broker gets Massachusetts data from, and whether it has called v3.openstates.org for MA, 2026-11-02

Ramon asks: because Massachusetts is not in the broker's replica list (`DDP_OPENSTATES_JURISDICTIONS` / the manifest's `replica_routing`), **has the production broker been making calls out to v3.openstates.org for anything about Massachusetts?** I do not know. From the code I can only say the replica list decides "which source a bill is read from" for the states on it (`search/openstates_search.py:235`, `views/openstates_api.py:317`); I have **not** shown what the broker does for a state that is not on it, and an earlier line of mine saying MA data "goes somewhere else" was a guess. Please read, don't assume.

**Nothing here changes anything: do not restart, edit, deploy or call any outside service yourself.** Do not print secrets or key values (names and counts only). Anything the logs do not record: say "not readable", do not estimate.

## What I need, from the production broker host (read-only)
1. **Does the broker call the public service at all?** Is `OPENSTATES_API_KEY` set in the broker's environment (yes/no, never the value), and does the broker's code path for a **non-replica** jurisdiction build a request to `v3.openstates.org` or to something else? Name the host the broker's OpenStates client points at for replica states and for non-replica states (the base URL settings, host part only).
2. **Evidence of outbound calls about Massachusetts.** In the broker's web and celery logs (and nginx or any outbound/proxy log you have), count lines that show a request to `v3.openstates.org`, split by jurisdiction where the line says which one (MA against each replica state), per day for as many days as the logs go back. If the logs do not record outbound calls at all, say so plainly; that is itself the answer to "can we prove it".
3. **Inbound Massachusetts traffic.** How many requests the broker itself received that name Massachusetts (bill lookups, session or jurisdiction lookups, `ensure`, search, `/explore` filters with `ma`), per day, same window. Is MA reachable from any public page today? If there is almost no MA traffic, then the broker may simply never have needed to call out for MA.
4. **LegBot and the sync path.** For MA bills, does ddp-sync fetch from the replica (its list includes MA) and does the broker then read the bill from its own database? One example MA bill id and where each step read it from, if you can show it from logs.
5. **Network evidence, if any exists:** DNS query logs, VPC flow logs or proxy logs on the broker host for `v3.openstates.org`; say which of those are enabled.

## Reply
A short table: question, what you read, the number or "not readable". State plainly at the end: **proved yes, proved no, or cannot be proved from what the host records**. I will put your answer on OPEN-68 and OPEN-318.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
