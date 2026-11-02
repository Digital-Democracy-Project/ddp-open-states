# Request: one read-only count to settle Jay Adams's numbers (OPEN-481), 2026-11-02

Thank you for `72a3e3a`. The release is accepted as done; this is only the one check that is still open. The route returned **485** votes for Jay Adams on EC2 (yes 462, no 9, absent 9, abstain 0, "not voting" 5), against **481** (459, 9, 9, 4) on the Mac replica. The route sums to its own total, so it looks consistent; what is missing is an **independent** count (a plain query, not the route) on the database the EC2 api-v3 reads, which is what the ticket's acceptance asks for. **Read-only; change nothing.**

## What I need
1. Run these as `SELECT`s against **the same database the EC2 api-v3 container reads** (the one `/bills?jurisdiction=nc` answers 2,343 from). Do not print the connection string or any credential.

```sql
-- A. the count the route should equal
select option, count(*) from opencivicdata_personvote
 where voter_id = 'ocd-person/1a75f967-8f35-40aa-8b0a-990a135e70cb'
 group by option order by 2 desc;

-- B. date range, and when his vote events were last changed
select count(*), min(e.start_date), max(e.start_date), max(e.updated_at)
  from opencivicdata_personvote v
  join opencivicdata_voteevent e on e.id = v.vote_event_id
 where v.voter_id = 'ocd-person/1a75f967-8f35-40aa-8b0a-990a135e70cb';

-- C. the first three rows in the route's order
select e.id, e.start_date, v.option
  from opencivicdata_personvote v
  join opencivicdata_voteevent e on e.id = v.vote_event_id
 where v.voter_id = 'ocd-person/1a75f967-8f35-40aa-8b0a-990a135e70cb'
 order by e.start_date desc nulls last, e.id desc, v.id
 limit 3;
```

   (I ran the same three on the Mac replica, read-only, so you know they are valid. **Mac values for comparison:** A = yes 459, no 9, absent 9, abstain 4; B = 481 rows, 2025-01-08 to 2026-08-05, `max(updated_at)` **2026-08-31 22:04 UTC**; C's first id is `ocd-vote/6efb4a58-143a-43e6-8538-5b13f01332df`. A later `max(updated_at)` on EC2 would fit the Mac replica being older than the database EC2 reads.)

2. **Compare and reply** (state codes and numbers only):
   - **A** against the route: **485 total; yes 462, no 9, absent 9, "not voting" 5**. If A matches, the route is right and the 481 was true of the Mac replica only; say so.
   - **C** against the route's first page: the first three `vote_event.id` values from `GET /people/<id>/votes?per_page=3` should equal C's three ids, in order.
   - **B**: just the values (a recent `max(updated_at)` would explain the difference from the Mac).
3. If A does **not** match 485 / 462 / 9 / 9 / 5, or C's ids differ: **change nothing**, report the numbers you read, and I will look at the route.

## Not asked
No restart, no deploy, no write of any kind. The broker release is Ramon's `/broker-deploy`.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
