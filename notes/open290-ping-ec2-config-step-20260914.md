# OPEN-290: ping on the remaining EC2 config step

PR #153 is merged (your own review comment confirmed it, Jira comment 15258) -- the
override code is live on `main` now, so `LEGBOT_SCRAPE_COMPLETION_TRIGGER_ARTIFACT_TYPES`/
`_LIMIT`/`_INCLUDE_CONCEPT_STATEMENTS`/`_ENABLED` set in EC2's real container environment
will actually take effect.

Checking in on the one thing you flagged as still open on your own last comment: setting
the real values in `docker-compose.prod.yml` and verifying the WireGuard-relayed dispatch
end-to-end. Anything blocking that, or just queued behind other work? Let us know if
there's anything we can help unblock from this side.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
