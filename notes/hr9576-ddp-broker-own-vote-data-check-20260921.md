# Read-only check against ddp-broker's own production Postgres: Bean/Carter actually resolve correctly there, right now, for this exact vote

**Re:** the whole VOTEBOT-7/OPEN-2 thread on this branch. Ramon had me read `ddp-broker-py`'s
own repo (models, not raw credentials) to understand its DB access pattern precisely, then run a
genuinely read-only Django-ORM check against its production Postgres -- the same
`docker exec ddp-broker-py-web-1` pattern already used earlier this session for the Bill/
BillArtifact counts. This is a **separate database from the OpenStates RDS instance**
(`opencivicdata_*` tables) the earlier note's SQL was written against -- still no access to that
one from this host without raw-credential hunting, which isn't happening. But `ddp-broker-py` has
its own independent copy of vote/representative data, synced from OpenStates, and checking it
directly turned up something that complicates the working theory.

## What I found: HR9576's roll call 309, as ddp-broker actually has it stored right now

`Bill.objects.get(gov_id="HR9576")` (id 8091) -> `Motion` id 4707, "On Passage", rollcall_num
309, date 2026-09-16 22:37 UTC -- matches everything confirmed earlier. Queried its `Vote` rows
directly:

```
Aaron Bean  -> yes, R-FL-4
John Carter -> yes, R-TX-31
Buddy Carter -> yes, R-GA-1
Troy Carter -> no,  D-LA-2
```

**All four resolve correctly, right now, with correct party and district**, in ddp-broker's own
live data for this exact vote -- not "Unknown," not missing. This is the opposite of what I
expected going in, given the earlier notes on this thread.

## A clue as to why: `also_known_as` already carries a manual disambiguation fix

`Representative.also_known_as` (a plain array field, used as a name-alias fallback for matching
vote records against -- see the model's own docstring: "the alias will be added to this list to
improve future lookups") already has, for exactly the House members sharing a surname:

```
Aaron Bean:   ['Bean (FL)']
Buddy Carter: ['Carter (GA)']
John Carter:  ['Carter (TX)']
Troy Carter:  ['Carter (LA)']
```

Every OTHER "Carter" in the table (Tyrone Carter, Brenda Carter, Neal Carter, Pamela Carter --
all state-level, not federal) has an **empty** `also_known_as`. This looks like a targeted,
manual fix applied specifically to the federal same-surname collision cases at some point, in
`ddp-broker-py`'s own separate sync/matching layer -- independent of whatever `resolve_person()`
does upstream in the OpenStates importer. If this is right, it would mean the underlying
OpenStates-side ambiguity bug (whatever it turns out to be) may already be worked around, in
practice, for public-facing ddp-broker/VoteBot display -- even if it's still real and unfixed
upstream.

**Don't know who added these aliases or when** -- no git blame done on the data itself (it's a
DB row, not code), and I don't have a way to see when `also_known_as` was last written from here.
Worth asking whoever has DB audit-log access, or just asking Ramon directly, before assuming this
"fix" is durable/complete rather than a prior one-off patch for exactly these 4 people.

## The one real discrepancy: 429 votes recorded vs. 433 expected

api-v3's own vote object for this motion: `yes=352, no=72, not_voting=9, abstain=0` = 433 total.
`Vote.objects.filter(motion=m).count()` in ddp-broker: **429** -- a gap of 4, not the "~95-97
members fail on every vote" scale described in the original investigation. `Vote.representative`
is a non-nullable FK (`on_delete=CASCADE`, no `null=True` in the model), so a voter that fails to
resolve during ddp-broker's own sync doesn't produce a row with a blank/null representative --
it's simply absent from this table entirely, which is consistent with "some voters are missing"
rather than "some voters show as Unknown". Didn't chase down exactly which 4 are missing (ran out
of a clean way to build the "full current House roster" comparison query without more trial and
error against `District`'s schema -- `chamber` there is itself a FK, not a plain string, so a
same-surname theory can't be quickly cross-checked from here beyond Bean/Carter specifically).

## Net effect on the working theory

This doesn't rule out a real `resolve_person()` bug upstream -- it just means, for this specific
bill and today's live `ddp-broker` data, the practical public-facing impact (the thing that
actually generates "Unknown" party displays) doesn't currently reproduce for Bean or any of the
three federal Carters, and the gap between expected (433) and actual (429) vote rows is much
smaller than the "~95-97 every vote" figure. Worth reconciling: is that 95-97 figure from a
direct read of the raw OpenStates `opencivicdata_personvote` table (which would show the bug
before any of `ddp-broker`'s own alias-based workarounds get a chance to compensate), or from
something user-facing? Those could show very different pictures of the same underlying bug.

Reply on this branch as usual.
