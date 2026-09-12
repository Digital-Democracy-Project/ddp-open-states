# Real production ddp-broker config does NOT point at the Mac -- likely stale assumption from a dev checkout

Checked the actual live containers (`docker inspect ddp-broker-py-celery-1` /
`ddp-broker-py-web-1`), not a checked-out `.env` file, per your own note's request.

## What's actually deployed here, right now

```
DDP_OPENSTATES_API_ROOT=https://api.digitaldemocracyproject.org/openstates
DDP_OPENSTATES_JURISDICTIONS=MI,UT,US,VA,AZ,WA,FL
```

**Not** `http://host.docker.internal:8002` (the Mac's `api-v3`). Also 7 jurisdictions live,
not 8 -- `NC` isn't in the actual running config (matches an already-known, separate gap:
NC has never been fully onboarded to the live schedule -- see this session's own memory on
that, unrelated to tonight).

## Verified this endpoint is real, healthy, and independent of the Mac

- `api.digitaldemocracyproject.org` resolves to an external IP (`52.204.100.187`) --
  confirmed this EC2 host's own nginx does NOT front that domain (its config only serves
  `mapapp.digitaldemocracyproject.org`), so it's hosted somewhere else entirely, with its
  own infrastructure.
- With the real bearer token from the live container: `GET .../openstates/openapi.json` ->
  `200`, real OpenStates API v3 metadata.
- **`GET .../openstates/people?jurisdiction=mi&per_page=1` -> `200`, one real result** --
  this is the exact call path (`get_people`/`update_representatives_for_jurisdiction`) your
  note was worried about breaking tonight.

## Conclusion (flagging, not declaring done unilaterally)

Production `ddp-broker` on this host does not appear to depend on the Mac's `api-v3` at
all -- it's already pointed at what looks like the real, separately-hosted, fully-working
production OpenStates API. If that's correct, repointing/restarting `ddp-broker` isn't
actually needed to protect tonight's run, and doing so anyway (pointing it at INFRA-1's
EC2 instance instead) would be a real, disruptive, unforced change to a config that's
currently fine.

**Before I do anything further here** (touching a live production service's config +
restarting it is exactly the kind of action I hold for explicit confirmation on): can you
or Ramon confirm whether `api.digitaldemocracyproject.org` is itself already backed by the
same 7-table-limited database the Mac's local `api-v3` is being repointed to, or is it a
fully separate, RDS-backed deployment (which the healthy `/people` result above suggests)?
That's the one thing I can't confirm from here without knowing where that domain's own
backend actually lives.
