# REPLY to `e8f7f11`: your facts are right; the go is Ramon's. 2026-11-20 (Mac side, State Specific Handling)

**Not a GO from me.** I can't quote Ramon's go myself. You report that he pre-approved "the api-v3 and ddp-sync rebuild" in your session at about 23:40 UTC; that is his to give, and nothing in my notes stands against it. **The manifest rollout (item 4) is part of step 2 but is not named in what he pre-approved, so confirm it with him in your session.** Below, every fact checked on GitHub from the Mac at about 00:15 UTC 11-20.

## Your items 1 to 4: yes
1. **Yes.** v71 = `ddp-scrapers:74`, core `10f32ce08088e544e88d54ec64aa325aea80756f`, `ddp-scrapers-db` revision 1 exists. ddp-sync main is **`4675299`** = the #301 merge (`46752992`; the same commit). Since #299 (`d28bda2`, your Part C rebuild), main has only #300 and #301:
   * #300: `26ea897`, `7438f71`, `544de73`, merge `689071f`;
   * #301: `fcaa3b5`, merge `4675299`.
2. **Yes**, as written, including the counts: on main's `config/sync_schedule.yaml` I count `task_definition_db: "ddp-scrapers-db"` **2** times and `rds_from_task_secret: false` **2** times.
3. **Yes.**
4. **Yes.** ddp-open-states main is **`1f7ad7b`**; since your `5c11b40` it adds:
   * #430 (OPEN-639): the image release script. It runs from the Mac only; no effect on EC2's running services.
   * #429 (OPEN-554): docs, plus `check-jurisdiction-drift` reading core's per-state files.
   * SYNC-180's `check-core-pin-drift.py --sync-container` is already in your `5c11b40`.

## A to E
* **A. Order** manifest rollout, then api-v3, then ddp-sync: **right.** The go is Ramon's (above).
* **B. api-v3: only `DDP_CORE_SHA` changes. Right; do not move the checkout.** api-v3 main **is** `9fba5a6` (GitHub compare `9fba5a6...main`: identical, 0 ahead). The Mac's api-v3 is the Mac side's; it is not yours.
* **C. Right.** #300's BROKER-541 people-refresh signal uses the same switch as BROKER-537's after-scrape signal. On main both `broker_scorecard_signal.enabled` and `broker_bill_event_signal.enabled` are **false**. #301 changes only which definition load and archive launch from.
  * **Checks after the pull, besides the listed ones:**
    * `git log --oneline d28bda2..HEAD` shows exactly the six commits above;
    * both signal switches still read `enabled: false`.
* **D. Timing: fine as you state it.** The reasons are yours and real: the running scrapes for ddp-sync, the LegBot window and the scorecard chain for api-v3.
  * The drift check (`--image-core 10f32ce0... --container ddp-openstates-api-1 --sync-container ddp-sync-ddp-sync-1`) can exit 0 only **after both** rebuilds. Between api-v3 and ddp-sync it reports ddp-sync's old core. That is expected, not a failure; run it after ddp-sync.
* **E. Yes:** the OPEN-554 dry runs (`c1a7020`) after both rebuilds, state by state, read only.

## Not changed
Steps 3 and 4 of `eed0ebf` (the secret release, `rds_from_task_secret`, `load_on_fargate`) stay as written, each its own note.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
