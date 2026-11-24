# Reply (2026-11-24 00:29 UTC): Idaho 2026 re-import (`7788700`, `c77027a`, OPEN-779/781/787/798) DONE. Every pass/fail number passes.

Ramon: "Yes, all four runs and both previews" (my session, 11-23). **Run id-c73cf0b57182**, rev **86** (v84), triggered 23:53:21 UTC after core `0f3c24c9` fixed the loader; the first v84 run (`id-5f440952e865`) had collected but its load failed because of that loader breakage (`7dad3a9b`).
- **Timeline:** collection done 00:09:40; **load done 00:11:41** (1,095 s); archive task done 00:13:13 (91 s); `openstates_pipeline: done archived=True failed=0 status=completed duration 1,187.1 s`. No "already imported".
- **Counts (RDS, read only, 00:30 UTC):** Idaho 2026 **817 bills, 853 vote events** (as before).
- **Your pass/fail:** (1) **unmatched person votes: 0 of 45,990** (before **48**): **pass**. (2) **roll calls with a double vote: 0** (before **15**): **pass**. (5) **House votes per substitute: Grayson Stone 461, Kirk Larsen 82, Lisa Cannon 55, Gayle Batt 53, Trevor Chadwick 50, Max Brown 42, Randolph J. Hill 40, William Athay 37, Jennifer Beazer 32, Megan Woller 23, Jeff Carlson 14, Kenneth Zaken 14**: **exactly your list**: pass. (6) **Don Hall's 2026 House votes: 0** (before **461**): pass. **Senate acting senators:** Lesli Bjerke 351, Steve Keyser 11, Garrett Bjerke 4, Elisha Toews 2 (OPEN-781's 368); Darl Bruner 28, Joan Hawkins 10, Zach Brooks 6, Brian Merrell 4 (OPEN-779's 48): all as expected.
- Not run: the api-v3 call (needs the key).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
