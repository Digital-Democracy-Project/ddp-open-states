# UPDATE to `c1d800d` and `2fe49e7`: Florida's gate is approved, so the step 3 image can be built; the heads have moved (onboarding-only). 2026-11-21 20:50 UTC (Mac side, State Specific Handling)

**Still not a GO for the prod agent.** Ramon takes this request to the prod agent; the build itself is Ramon's (`deploy-scrapers-image.sh` on the Mac).

## The decision `c1d800d` asked for is made
* **Ramon, 2026-11-21 (recorded on OPEN-642): "Approve now"** for Florida's scorecard gate list (OPEN-642 comment 22288).
* **What the list found** (73 of the 90 polled Florida 2026 bills, measured on a dev copy at broker `92fe8bdf`):
  * #187 adds 171 links, 48 of them companions;
  * **0 scorecard files change, 0 votes start or stop counting, 0 new broker links.**
* The other 17 bills are added on the ticket when flsenate.gov answers again, and flagged only if one would change a scorecard.
* **Ramon: "Keep as companions"** for the 13 same-chamber "companion bill(s) passed" links. No scraper change.
* So **Florida's scheduled scrape stays as it is** (no pause), and #187 ships in this image.

## The heads now (the build clones main; check its log)
| Repo | Now | New since `c1d800d` / `2fe49e7` |
|---|---|---|
| openstates-core | `7f5319583f9d30684ef3f042ea308554f1cc0676` | #127 (OPEN-552, Arizona `classify_action`, in `2fe49e7`); **#137 (AGENTS-250): test scripts only** (`.codebot/`), no runtime change |
| openstates-scrapers | `2470de84db52ac3d3f744ad56ec0f5d25eabc1b0` | **Onboarding states only, none scheduled:** ME #188, MO #189 (2022S1 end date), IA #191, MD #192 (2026 special session). #190 (AGENTS-250) is test scripts only |
| ddp-open-states | `237f1f8c2e59cf0613f2959646cf47f67d77e258` | chamber names for ME, IA, MD in `jurisdictions.yaml` (#451 #452 #453), probing states only |

* **Step 4** uses the image's core: `DDP_CORE_SHA=7f5319583f9d30684ef3f042ea308554f1cc0676`, or whatever the build log shows. #137 changes no runtime code, so `948be01b`'s behaviour stands.
* Anything newer than this table in the build log needs its own look before registering.

## Unchanged
Everything else in `c1d800d` and `2fe49e7`:
* the after-registering steps;
* step 4 (`request-1f1e692-step4-api-v3-ddp-sync-core-130c40bd-20261121.md`, with the core above);
* the follow-ons waiting on this image (OPEN-659 reports, SYNC-181's US re-import, Arizona's relabel request, OPEN-642's re-import);
* what is not authorized.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
