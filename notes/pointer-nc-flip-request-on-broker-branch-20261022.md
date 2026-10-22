# Pointer: the NC flip request is on the ddp-broker-py ops-handoff branch

Ramon's go for routing NC to the replica (BROKER-302), with the prerequisite steps (pull /opt/ddp-open-states, deploy ddp-sync main, load NC's people into RDS, parity gate, then the flip) is in `notes/request-flip7-route-nc-to-the-replica-BROKER-302-20261022.md` on **ddp-broker-py's** `notes/ops-handoff` branch (commit 90d1e530). It also answers your open question from the OPEN-330 reply: please report there whether the 2026-10-20 .env edit removed an NC added earlier. Steps B and C touch this repo's checkout on the EC2 host. Do not print secrets: read variables by exact name only.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
