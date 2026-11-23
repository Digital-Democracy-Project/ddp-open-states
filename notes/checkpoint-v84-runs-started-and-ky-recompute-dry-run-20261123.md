# Checkpoint (2026-11-23 23:17 UTC): three v84 runs started on rev 86; Kentucky recompute dry run: every number in range. No commit.

Ramon, in my session (pop-up, 11-23 ~23:10 UTC): "Yes, all four runs and both previews". Notes re-fetched before each step (none withdrawn).

## v84 (ddp-scrapers:86): one POST each, 202, no retry (23:15:28 to 23:15:38 UTC)
| State | Call | Run id | Revision (ECS) |
|---|---|---|---|
| id | `openstates-scrape/id?full=true&sessions=2026` | **id-5f440952e865** | **ddp-scrapers:86** |
| md | `openstates-scrape/md` | **md-efa89d747d32** | **ddp-scrapers:86** |
| mt | `openstates-scrape/mt?full=true&sessions=2027` | **mt-da06a3dfea66** | **ddp-scrapers:86** |
Montana's step-1 gate (api-v3 and ddp-sync at core 9157b6b5) holds (drift exit 0, `da4f6955`). **Iowa 2025** is **not started yet**: Iowa's resumed 2026 run (`ia-826c2805ac5e`) is still collecting, and two Iowa loads at once is not what your request asks; I will trigger `ia?sessions=2025` after Iowa 2026 loads. Idaho's pass/fail (SQL incl. House substitutes, before: 48 unmatched, 15 double votes, Don Hall 461), Maryland's and Montana's reports come when they load.

## Kentucky `recompute-diff-order ky --dry-run` (read only, core 9157b6b5, 23:16 UTC)
- **The rule is present:** `note_stage('Current/Final')` returns `(2, 0.0)` (chamber passage) in the ddp-sync container's core.
- `ky: [DRY RUN] 1707 bills checked | unchanged=1750 corrected=811 nulled=0`; `is_bill_version: set=0 changed=0 not_a_version=0`; `diff_baseline_id: set=652 changed=179 cleared=0`; exit 0.
- **Your ranges:** corrected 760-860 (**811**), set 620-680 (**652**), 0 nulled, 0 cleared, no error: **all inside**; identical to your Mac-replica measure (`corrected=811`, `set=652`, `changed=179`).
- **List:** `notes/ky-recompute-dry-20261123/ky-recompute-dry-core9157b6b5-20261123.csv`, **831 documents**, md5 `d21f9eb840921a26bd7cfd8bf463724e`. **Not run:** the stored-comparison backup export (I could not find your NM export recipe; the document table is `ddp_bill_version_document`); I will do it at commit time. **No commit:** it waits for Ramon's second go after he has seen these numbers.
- **Oklahoma recompute dry run:** held until the Oklahoma re-import has loaded both sessions and been verified (2025 loaded 20:52; 2026 is collecting again after the restart: `ok-b13efe4b9c89`).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
