# OPEN-193 AC6: real per-jurisdiction RDS freshness measurement

Ran this directly against RDS + `ddp-sync`'s own Redis flow-history (both real, live sources,
not inferred). Method: `opencivicdata_jurisdiction.latest_bill_update` (OpenStates' own
per-jurisdiction freshness field) for the age numbers, cross-checked against each
jurisdiction's actual scheduled cadence and real run history (Redis) to interpret them
correctly rather than just reporting raw ages.

| Jurisdiction | latest_bill_update age | Registered cadence | Interpretation |
|---|---|---|---|
| US | 0.9 days | daily | On schedule, fresh. |
| WA | 0.9 days | daily | On schedule, fresh. |
| FL | 6.9 days (last: 2026-09-06) | **weekly** (Sunday) -- see note below | On schedule for its *current* cadence. |
| VA | 6.9 days | weekly (Sunday) | On schedule. |
| MI | 6.9 days | weekly (Sunday) | On schedule. |
| UT | 6.9 days | weekly (Sunday) | On schedule. |
| AZ | 6.9 days | weekly (Sunday) | On schedule. |
| MA | 9.2 days (last real update: 2026-09-03) | weekly (Sunday) | **Its most recent scheduled run (2026-09-06) actually FAILED** (`success: false, failure_reason: "nonzero_exit_other"`, Redis `ddp:flow_history:openstates_secondary_scrapes:ma`) -- stale because of a real failure, not just quiet legislative activity. |
| NC | sentinel value (2021-01-01, never real) | weekly (Sunday), added 2026-09-09 | Not a bug -- NC's very first scheduled cycle is *tomorrow* (2026-09-13, this jurisdiction's Sunday slot), added too recently to have run yet. |

**FL's cadence needs a flag of its own, unrelated to freshness being "wrong" right now:**
`sync_schedule.yaml`'s own header comment still says "Daily: FL" but the real registered
cadence (confirmed via `ddp-sync`'s own log: `openstates_fl_scrape: registered
effective_cadence=weekly sync_day=sunday sync_time=02:00`) is weekly. This is a **deliberate,
already-documented** manual demotion (OPEN-140's `dynamic_cadence` section, still `enabled:
false`) tied to FL's session status -- the file's own comment says exactly this: *"Florida
currently carries this logic as a comment and a reminder -- 'Remove sync_day (revert to daily)
once the 2027 session opens' -- and if nobody remembers in November, FL scrapes weekly through
its entire session."* FL's current active sessions in RDS (`2026`, `2026F`) both have
`end_date`s already in the past (2026-03-13, 2026-06-05) -- FL is genuinely out of session
right now, so weekly is the correct cadence today. **Flagging the exact risk the code comment
already names**: this is a manual `sync_day` edit with no automatic reversion -- someone needs
to remember to flip it back once FL's 2027 session opens, or it'll silently stay weekly through
an active session.

**Real action item, not a documentation gap: MA's last scheduled run failed and nobody has
retried or investigated it.** I could not find the underlying error (this container's own log
buffer has rotated past 2026-09-06 due to at least one restart since; the CloudWatch log-stream
naming for these Fargate tasks doesn't include the jurisdiction, so finding the specific failed
task's logs needs cross-referencing stopped-task history around that timestamp -- didn't do
that digging myself since it's a separate investigation from the freshness measurement itself).
Someone should look at why MA's 2026-09-06 run failed (`nonzero_exit_other` is generic) and
whether it's recurred since -- if it hasn't been retried, MA will stay stale until the *next*
Sunday's run, assuming that one succeeds.

**Summary for AC6**: the live feed (`cloud_path`) is genuinely running and, for 7 of 9
jurisdictions, freshness matches each one's actual registered cadence with no gap. The 2
exceptions are both explained by real, specific causes (FL: deliberate cadence demotion,
documented and expected; MA: an actual run failure needing attention) -- not a systemic
freshness problem. NC is a non-issue, just too new to have run yet.
