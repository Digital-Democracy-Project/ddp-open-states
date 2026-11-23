# Reply: OPEN-648 Michigan full run LOADED (resumed through the 07:39 rebuild); related links as expected, none companion

From DDP Prod Agent, 2026-11-23 14:29 UTC. Run **mi-b8b23c2b5df9**, task revision 81 (v79), triggered 04:24:37 UTC (`afa4cc05`).

- **Timeline:** collection and load took **24,546 s (6 h 49 min)**; `cloud_scrape: done` at **14:28:08 UTC**. **The 07:39 rebuild restarted ddp-sync in the middle**; the run **resumed from redis** (07:39:02, `cloud_scrape: resuming a Fargate job orphaned by a previous restart`) with a fresh wait budget and loaded without a retry. Its archive step was not run by the resumed run: I triggered it by hand at **14:29:01 UTC** (`POST openstates-archive/mi`, 202; Ramon's overnight pre-approval). I will report it when it ends.
- **Bills (RDS):** session 2025-2026: **4,312**.
- **Related-bill links, session 2025-2026 (RDS, read only):** **related 3,120 and companion 0**. By label: "House Fiscal Agency Analysis" 1,792; "Senate Fiscal Agency Analysis" 1,014; "Senate Fiscal Agency Analysis; House Fiscal Agency Analysis" 314. Before: 0 related. Your measure was about 2,270 on 765 bills; the loaded total is higher (3,120); I have not looked at why (the cached pages you measured on may differ from today's).
- **Spot check:** HB 5807 lists HB 5805, HB 5806 and SB 966, each `related` with the joined label "Senate Fiscal Agency Analysis; House Fiscal Agency Analysis".
- **Not read:** "mode full" line, firewall-block lines, vote counts, fetch errors. Broker: no action asked; Michigan's BillRelation count not re-read by me yet.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
