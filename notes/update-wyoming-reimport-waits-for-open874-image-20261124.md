# UPDATE (not a GO) to `ea0ef64`: **Wyoming's re-import waits for the image that carries OPEN-874** and runs once, on it. Everything else in `ea0ef64` stands. 2026-11-24 ~21:30 UTC (Mac side, Onboard New States)

**Not a GO.** Ramon confirmed the rule today (via the PM session): every full up-or-down roll call on a bill counts and the latest replaces earlier ones.

* **Wyoming** (OPEN-874): all earlier-reading roll calls count (139 bill-chambers: failed introduction, introduced and referred, failed Committee of the Whole), and only **whole-bill** veto overrides count (not the 14 SF 1 line items). It is a Wyoming scrapers label change plus **a new image and one Wyoming re-import**.
* **So: keep holding Wyoming's re-import** (`e30bb8e` 4a, `9e63a3d` batch 1) **until the OPEN-874 image exists**, then run it **once** on that image. If Ramon wants Wyoming's data for Broker Upgrades sooner, that is his call: Wyoming would then run now and again later.
* OPEN-872 (Oklahoma roll-call number), OPEN-873 (Rhode Island missing roll calls), OPEN-875 (Utah) and OPEN-876 (Nebraska advancement) are **not assigned or built yet**. Nothing in your order depends on them yet. I'll post a note when one needs a release step.
* **Unchanged:** one core rollout at `70146fac`, then the parallel re-imports, the backfills and the Maine archive (`ea0ef64`).

Tickets: OPEN-874 (blocks BROKER-589), OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
