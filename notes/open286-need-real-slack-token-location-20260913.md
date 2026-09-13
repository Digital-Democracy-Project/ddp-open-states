# OPEN-286: need the real Slack bot token's location, not just confirmation it exists

Following up on `notes/open285-286-progress-20260913.md` -- everything on this side is ready
and tested; the only missing piece is the actual credential.

Your earlier note said `ddp-agents`' own `failure_watcher.py` already listens on
`#automation-errors`, so a working bot token for that channel exists somewhere in the fleet.
Can you go find it and tell Ramon (and me) exactly where it lives -- which secret/host/`.env`
file, and the specific key name -- so he can go copy the real value himself, the same way he
just sourced `ddp-broker-py`'s token directly rather than granting this host's role any new
secret access?

Once we have that, the fix is a one-line swap: update `slack_bot_token` in the
`ddp-sync/credentials` Secrets Manager secret to the real value, restart `ddp-sync`
(`systemctl restart ddp-sync`), and I'll re-run the same `chat.postMessage` test I already
have ready to confirm it actually reaches the channel this time.
