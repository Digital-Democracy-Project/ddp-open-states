# OPEN-1: S.2 Senate party-vote reversal — root-caused to motion misclassification, not vote data (2026-08-05)

## The report

Jira OPEN-1 (Sadie Holzmeyer, 2026-07-24): the digitaldemocracyproject.org scorecard for S.2
(Secure America Act, 119th Congress) showed the Senate vote as if Democrats voted for the bill
and Republicans against it — the reverse of reality (this was a party-line reconciliation bill).
House side looked correct. Reporter's hypothesis: "the votes are misclassified from Plural"
(the public Open States API).

## Investigation, step by step

### 1. Ruled out vote/party data entirely

Compared the Senate passage roll call ("On Passage of the Bill S. 2", 2026-06-05) across three
independent stores:

| Source | Result |
|---|---|
| `ddp-open-states`'s own scrape (`senate.gov` roll-call XML directly) | 52 R yes; 44 D + 2 I + 1 R no; 1 D not-voting |
| Public Open States v3 API (`v3.openstates.org`) | identical to above |
| `ddp-broker-py`'s own `common_vote`/`common_role` (date/chamber-scoped) | Republicans → yes, Democrats/Independents → no |

All three agree and are correct. **The "Plural has bad vote data" hypothesis is false.**

Note: `ddp-broker-py` (not `ddp-sync`, which only builds RAG/chatbot content from *already
published* Webflow copy) is the service that actually renders bill scorecards for the Webflow
CMS — see its `scorecard/` app. It sources federal bills/votes from the **public**
`v3.openstates.org` API, not from `ddp-open-states`'s own scrape (confirmed:
`common_bill.openstates_id` for S.2 matches the public API's bill UUID
`2209fd8a-d5e0-4e6c-b93b-5960062457f6`, not `ddp-open-states`'s own `ocd-bill/1d2d492a-...`).

### 2. Found the real bug: motion misclassification, not vote data

The public Open States API tags `motion_classification: ["passage"]` on **every** Senate
roll-call motion for S.2 — not just "On Passage of the Bill S. 2", but also "On the Motion to
Proceed S. 2" and all four "Motion to Commit ... with Instructions" (recommittal) motions
(Ossoff, Warnock, Schumer, Wyden).

`ddp-broker-py`'s `fetch/interfaces/OpenStates/openstates_service.py:673` trusts this blindly:

```python
is_passage = "passage" in (motion_data.motion_classification or [])
```

So all 6 distinct Senate motions on S.2 end up `is_passage=True` in `common_motion`:

| Motion | Date | Result | `is_passage` | rollcall |
|---|---|---|---|---|
| On the Motion to Proceed S. 2 | 06-03 06:59 | pass | true | 136 |
| Ossoff Motion to Commit w/ Instructions | 06-04 07:51 | fail | true | 141 |
| Warnock Motion to Commit w/ Instructions | 06-04 12:36 | fail | true | 147 |
| Schumer motion to commit w/ instructions | 06-04 14:30 | fail | true | 137 |
| **On Passage of the Bill S. 2** | 06-05 08:42 | pass | true | 163 |
| Wyden Motion to Commit w/ Instructions | 06-05 16:40 | fail | true | 153 |

`scorecard/scorecard_views_v2.py:260-294` (`_get_latest_motions_for_chamber`) orders a chamber's
motions latest-date-first and picks the first `is_passage=True` one with a `rollcall_num` set.
Because the **Wyden recommittal motion (16:40) happened after the real passage vote (08:42) that
same day**, it wins the selection instead of "On Passage of the Bill S. 2".

A recommittal motion inverts yes/no semantics relative to bill support (voting "yes" tries to
send the bill back to committee / block it; "no" lets it proceed). Confirmed in `common_vote` for
the Wyden motion: Republicans voted "no" (~50), Democrats+Independents voted "yes" (~46) — the
exact inverse of the real passage vote. Rendering this motion's votes with passage-vote semantics
(yes = supports the bill) produces exactly the reported reversal.

The House side looked correct by coincidence, not design: its analogous "On Motion to Commit" is
*also* mistagged `is_passage=True`, but it happened before "On Passage" that day (21:10 vs 21:23),
so date-desc selection landed on the right motion anyway.

### 3. Confirmed `ddp-open-states` does NOT have this bug

Queried `ddp-open-states`'s own `opencivicdata_voteevent.motion_classification` (populated by our
own scraper, independent of the public API) for the same 8 S.2 motions — every one is classified
correctly: `['passage']` only on the two real "On Passage" votes, `[]` on all six procedural
motions (proceed + 4× commit-with-instructions).

To rule out a fluke, sampled 40 other US-Congress vote events with procedural motion text
("to proceed", "to commit"/"to recommit", "cloture", "previous question") across unrelated bills
(HR 4, HR 26, S 2882, SJRES 190, HRES 294, etc.) — **all 40 correctly classified `[]`**. Across the
entire US Congress `opencivicdata_voteevent` table, `motion_classification` only ever takes two
values: `['passage']` (970 rows) or `[]` (572 rows) — a clean binary split, no noise.

**Conclusion: the misclassification is entirely confined to the public Plural API's
classification pipeline for federal motions. `ddp-open-states` needs no fix.**

## Implication for the fix (lives in `ddp-broker-py`, not this repo)

Two viable approaches, both scoped into OPEN-1's acceptance criteria:

1. Patch `is_passage` in `openstates_service.py` to exclude known procedural motion-text patterns
   (`to commit`, `to recommit`, `to proceed`, `to table`, `previous question`, etc.) regardless of
   the public API's classification tag.
2. More durable: since `ddp-open-states` already classifies these motions correctly, have
   `ddp-broker-py` source federal motion classification from `ddp-open-states`'s own data instead
   of continuing to trust `v3.openstates.org` for this field — otherwise this class of bug will
   keep recurring per-bill as new Congress votes come in.

Also worth its own audit: any other 119th Congress bill where a procedural motion happens to be
the chronologically last roll-call motion on a chamber, after the real passage vote, will show
the same misdisplay. Not checked beyond S.2 in this investigation.

## Side findings (separate tickets, not this one)

- Every `Motion` on S.2 was imported twice into `ddp-broker-py`'s `common_motion` (e.g. "On
  Passage of the Bill S. 2" exists as both id 2343 and 3042, each with its own near-full vote
  set — 98 and 100 votes respectively).
- `ddp-broker-py`'s `get_or_create_roles_from_yaml` (`openstates_service.py:1657-1663`) sets a new
  `Role.party` by copying the person's most-recently-existing Role's party rather than reading
  party from the freshly-fetched OpenStates data — defaults to `""` for a brand-new
  representative with no prior Role. Produces missing/stale party, not a reversal; unrelated to
  this ticket's symptom but a latent correctness bug in the same code path.

## Disposition

Posted as three comments + a rewritten description on OPEN-1; ticket moved to **In Review**
(analysis complete, no code fix written yet — the actual fix belongs in `ddp-broker-py`, which
has no dev checkout on this machine as of this writing). See Jira OPEN-1 for the full comment
history and final acceptance criteria.
