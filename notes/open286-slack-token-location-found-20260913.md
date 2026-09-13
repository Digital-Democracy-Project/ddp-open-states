# OPEN-286: real Slack token location found on the Mac

Confirmed directly on the Mac Studio (this is where CAMS/Agent Smith actually runs, via
launchd) -- did not read or print the actual token value, only confirmed it's present and
where it lives:

- **File:** `/Users/agentsmith/Developer/repos/ddp-agents/.env`
- **Key:** `SLACK_BOT_TOKEN=` (present, non-empty -- confirmed via `grep -c`, value not read)
- **Confirmed this is the real one CAMS uses:** `com.ddp.cams-server.plist` (the launchd
  daemon running CAMS/Agent Smith) documents in its own comment that `start-cams.sh` sources
  exactly this `.env` file. `ddp-agents/src/agent_smith/config.py`'s `slack_bot_token` field
  falls back to this exact `SLACK_BOT_TOKEN` env var if no agent-specific token is set --
  matching `failure_watcher.py`'s own `#automation-errors` usage.

Ramon can copy the real value directly from that file on the Mac (same pattern as sourcing
`ddp-broker-py`'s token) -- I'm not relaying the value itself, just the location, per your own
ask. Once it's swapped into `ddp-sync/credentials` and the service restarted, your
`chat.postMessage` re-test should confirm it reaches `#automation-errors` for real.
