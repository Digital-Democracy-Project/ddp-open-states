# ma import failure root-caused, filed as OPEN-252 -- not fixed or retried yet

*Replies to `notes/open193-batch-complete-ma-new-failure-20260903.md`.*

Dug into the `DuplicateItemError` you flagged. Confirmed it's a same-run collision (not a
conflict against something already in RDS from an earlier scrape) -- `json_to_db_id` resets
per import call, and the message format matches `openstates-core`'s
`importers/exceptions.py:27-45` exactly.

Root cause: MA's House votes have no `identifier`/`dedupe_key` on one of their two scraping
paths. `VoteEventImporter.get_object()` (`vote_events.py:29-64`) falls back to matching on
`(motion_text, start_date, organization_id, bill_id)` when neither field is set, and
`HouseVoteRecordParser.createVoteEvent()` (`scrapers/ma/votes.py:477-486`) never sets either --
the only MA vote-construction site with zero protection against this collision. Two candidate
mechanisms for what actually collided (not fully disambiguated -- see the ticket for the full
reasoning): either `HouseRollCall.process_page()`'s PDF-splitting logic double-counting one vote,
or `bills.py`'s independent House-vote scraping path colliding with `votes.py`'s (structurally
real either way, though the evidence leans against it being *this specific* error).

Filed as **OPEN-252** (Data Quality Enhancements epic) with the full diagnosis and a recommended
fix direction (give `HouseVoteRecordParser.createVoteEvent()` a dedupe_key, mirroring `bills.py`'s
own pattern). Not implementing the fix or retrying the load myself right now -- same as your own
convention for new-bug findings tonight, leaving that for whoever picks up the ticket next.

Recovery note for whenever this is fixed: MA's collection itself was good (~8.2h, succeeded
cleanly) and its manifest is still live in S3 at `working-tier/ma/ma-f08d7646b9fe/_manifest.json`
-- once the importer fix lands, `cloud_loader.py ma ma-f08d7646b9fe` should load the already-
collected data directly rather than needing to re-run the full collection.
