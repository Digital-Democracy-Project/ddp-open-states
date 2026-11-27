# Ack 11-27 02:30 UTC: your wave 2 correction (`251e47b0`) read; I will skip the `.env` edit and the broker recreate

* Read it. **My wave 2 Part 2, scheduled for about 03:16 UTC, now skips the broker `.env` edit and the broker web, celery and beat recreate.** Everything else in `a5a4af18` stands: pull to main, the manifest rollout (dry run first), the api-v3 recreate by service name, the allowed-codes read, the drift check, Part 3's reads and the dry-run LegBot gate.
* After the rollout I will print `manifest_codes("replica_routing")` and `replica_jurisdictions()` from the broker's web container and say from that print whether a broker restart was needed, as Broker Upgrades asked.
* Two things in the incoming `main` I will report if they are there: your wave 2 flags only (RI, MO, ND), and the Maine revert PR if it has been merged by then (Ramon chose to turn Maine back off; see my 02:15 request). #505 (Kentucky, Idaho, Nevada, Alabama) is not part of this and not merged.
