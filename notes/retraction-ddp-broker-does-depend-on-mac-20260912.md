# Retracting my last note -- I was wrong, Ramon says api.ddp.org/openstates currently proxies to the Mac

My previous note here ("real ddp-broker config does NOT point at the Mac... false alarm,
no action needed") was itself wrong. Ramon just corrected it directly: 
`api.digitaldemocracyproject.org/openstates` -- the domain your own check found production
`ddp-broker` actually configured against -- currently proxies through to the Mac's local
api-v3. So the dependency is real, just indirect (ddp-broker -> that domain -> proxy ->
Mac's api-v3), not the direct `host.docker.internal:8002` path I originally assumed from a
stale dev-checkout `.env`.

This is also fully consistent with what you observed: your live
`GET .../openstates/people?jurisdiction=mi&per_page=1` -> 200 with a real result succeeded
because the Mac's api-v3 is STILL pointed at the old, full-schema database right now (OPEN-272's
repoint hasn't been deployed yet) -- so the proxy chain currently returns correct data. It
would very likely start failing once/if the Mac's api-v3 gets repointed to the new 7-table
database, exactly as my original note worried about.

**Net effect**: please disregard my last "no action needed" note. The original ask (get
production ddp-broker off a path that terminates at the Mac's api-v3 before it's repointed)
still stands -- Ramon is handling the direct correction with you, so I won't duplicate
further instructions here; just flagging that my retraction of the concern was itself
wrong, so the record here doesn't mislead anyone reading it later. On my end: I'm holding
off on deploying OPEN-272's repoint until this is actually resolved -- not proceeding on the
assumption I stated two notes ago.
