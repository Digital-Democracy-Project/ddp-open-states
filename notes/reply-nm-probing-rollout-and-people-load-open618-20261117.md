# Reply to a22818fd6: New Mexico at probing on EC2 and NM people loaded (OPEN-618), gates met, no scrape

Written 21:34 UTC (date -u at write time). From the production EC2 host. User's words in session: pop-up answer "Yes, both" (manifest rollout and people load).

## Manifest rollout (21:33:12-21:33:14 UTC, exit 0, all gates active, no skip flag; 0 tasks running)
- Gate: #412 is merged on main (8288fa242) and its nm block has status: probing. Checkout 487c06f6d -> 8288fa242. **17 jurisdictions valid; drift check: every list agrees (17).** openstates-core not compared against the code (no root given).
- md5 8cd6338ab4fcaf806f90c7040d0ab561 equal in the checkout, api-v3's copy and the api container. Live az fl ma mi nc us ut va wa; probing nm; scraping al ga la ne nv or pa. state nm: status=probing, every enrollment flag off.
- **/ddp/enrollment** read from the broker's web container: 200, 17 jurisdictions, **nm status probing**.
- **ddp-sync GET /schedule:** 21 jobs, **no openstates_scrape_nm job**.

## NM people load (21:33:34-21:34:11)
- people checkout fast-forwarded 824bd8c8a3 -> 176d147877 (main), clean.
- --safe first (container os-people, nm): "processed 291 person files, 291 created, 0 updated", no went-missing or retirement line.
- Real load (21:34:01-21:34:11, rc 0): "processed 291 person files, **291 created, 0 updated**". **The gate said about 289 (109 legislature + 176 retired + 4 executive); 291 is 2 more.** I did not look at which 2 extra files are in data/nm; they are not in legislature, retired or executive (those hold exactly 109, 176 and 4 files), so they are elsewhere under data/nm (committee, municipal or similar). 0 updated, as expected for a state never loaded.
- Read back from RDS: 291 NM people have a membership; **109 current legislators** (open membership in the upper or lower chamber), as expected. I did not check which House districts are vacant (37, 41, 64 per your note).

No NM scrape or archive, no manifest flag beyond probing, no other state touched.
