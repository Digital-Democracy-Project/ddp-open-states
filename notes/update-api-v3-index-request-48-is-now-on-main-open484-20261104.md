# Update to the index request `6c59836` (OPEN-484): api-v3 PR #48 is now on `main`, so building from `main` includes it. Nothing else changes.

My request `request-api-v3-build-the-bill-list-index-on-production-open484-20261104.md` said "do not pull #48". It was open then; it was **merged at 05:14 UTC as `14433582`** (a one-line change: the page's total count no longer sorts every row first; same number). The review session also merged ddp-open-states #330.

**What this changes for you: nothing in the steps.** Build the api image from `main` at `16c5168b` (the index) **or any later commit, including `14433582`**: both work. You still **do not recreate the running api container**, so #48's code does not go live in this step and your after-timing measures **the index alone**, as intended. #48 reaches production with the next api-v3 image deploy (Ramon's step, separate; it needs no `ensure`).

Everything else in the request stands: quiet moment, no import in flight, `ensure --bill-list-index` once from the new image, the real duration of the command, before and after timings with the first 20 bill ids compared, rollback `DROP INDEX opencivicdata_bill_latest_action_desc_idx;`. The phase-timing request `b76c23c` is still wanted.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
