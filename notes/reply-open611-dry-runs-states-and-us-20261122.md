# Reply: OPEN-611 dry runs (states and US). Nothing written. Lists and BEFORE checks attached.

From DDP Prod Agent, 2026-11-22 20:09 UTC. Read only on RDS and the production broker (`7ce53986`). No `--commit`, no `mode=commit`. Script from a scratch checkout at ddp-open-states `bbfd8c16f` (includes #459, NC Tillett). Files in `notes/open611-lists-20261122/`.

## relink-blank-voters.py (dry run, RDS)
| State | Summary line | CSV rows |
|---|---|---|
| wa | `wa lower 'Hunt': [DRY RUN] fill=673 left_blank=0` | 673 |
| ma | `ma lower 'Garcia': [DRY RUN] fill=8 left_blank=0` | 8 |
| mi | `mi lower 'Myers-Phillips': [DRY RUN] fill=9 left_blank=2` (the 2 are blank by design: Tonya Phillips is already a voter on them) | 9 |
| fl | `fl lower 'Garcia': [DRY RUN] fill=0 left_blank=0` | 0 (header only) |
| nc | `nc lower 'Helfrich': fill=814 left_blank=0` and `nc upper 'Tillett': fill=5 left_blank=0` (the script's NC case runs both; Tillett's commit waits for OPEN-765 per the script) | 819 |

All five equal your Mac-replica numbers (FL 0 is as you predicted; a Florida re-import is running on EC2 right now).

## US: backfill-vote-person-resolution
`POST /ddp-sync/v1/trigger/vote-person-backfill?mode=dry-run` at 19:49:51 UTC: 202, `"mode": "dry-run"`, run id **vote-person-backfill-dry-run-324bce6140f4**, Fargate task done in 95.4 s. Log: `Loaded 853 distinct person identifiers. Found 15 unresolved vote records with a usable note/identifier. Dry run complete. Would resolve 15 records (0 still unresolvable).`

The job's log does not print the rows. To give you the list, I ran the script's own selection and its own identifier lookup read-only on the host (same code, same RDS): `us-vote-person-dry-list.csv`, **15 rows, 15 resolve, 0 not**. Every row is Waltz (W000823, resolves to Michael Waltz): 11 roll calls on 2025-01-03 to 2025-01-16 on HRES 5, HR 29, HR 23, HR 192, HR 152, HR 153, HR 28 (two), HR 164, HR 144, HR 33, HR 30 (two). Columns: personvote id, voteevent id, date, session, bill, voter name, option, identifier, person id, person name.

## Scorecard BEFORE values (production broker, read only; `before-checks.txt`)
- `validate_scorecards --jurisdiction <ST> --all`: **WA** 161 legislators / 3,672 votes, **MA** 11 / 1,995, **MI** 165 / 7,434, **FL** 229 / 27,376, **NC** 20 / 2,949: each 0 eligible votes missing, 0 not-up-or-down, "all validated". **US**: chamber/text check clean and undecided check clean; 0 legislator scorecards on the broker (reconcile also scans 0), so there are no US legislator scorecards to compare.
- `validate_scorecards --bills --all`: 859 bills, 131,898 votes, "all bill scorecards validated". It also prints **53 Utah chamber/text mismatches** (all Utah, motion text "House/..." recorded as upper and the reverse); I have not re-investigated them today. My 09-15 validation notes call the old Utah chamber-swap data harmless orphaned duplicates.
- `reconcile_scorecards --jurisdiction <ST>`: WA, MA, MI, NC, US agree on every recorded vote; **FL** has no unexplained mismatches, 2 pairs set aside as later revotes (BROKER-120).
- Undecided motions (eligible NULL): FL 27, US 3, all bills 33; none a passage vote on a scorable bill.

Not run: any commit, any people load, any other script.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
