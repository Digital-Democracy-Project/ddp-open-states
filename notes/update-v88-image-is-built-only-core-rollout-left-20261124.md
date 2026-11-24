# UPDATE (not a GO) to `e30bb8e` and `9e63a3d`: **the v88 image is already built.** Don't wait for a v88 build; what is left for v88 is the core rollout. The image still to be built is **v89**. 2026-11-24 ~20:30 UTC (Mac side, Onboard New States)

**Not a GO.** Nothing else changes.

* **v88 is built and registered** (Ramon ran `deploy-scrapers-image.sh`): tag `v88`, task revisions **`ddp-scrapers:90`** and **`ddp-scrapers-db:17`**, core **`0d373728ff8fd18308a689542b0ded7ec7d11d8b`**, scrapers **`0aba6be6`**.
* **Checked on the Mac** from the local image: `DDP_CORE_COMMIT` is `0d373728`, and the fixes for HI, MO (#273), KY, MS, MD, ME, MT, NV (#265, #269, #272), WA and WY are in it. **#279–#283 are not** (they are v89).
* **So in `e30bb8e`:**
    * **step 2 ("image v88, Ramon") is done;**
    * **step 1 is what remains:** the core rollout at `0d373728` (EC2 and Mac api-v3 at `254389aa`, EC2 ddp-sync at `eefb1ba`+ with `DDP_SCRAPERS_SHA` as in `a0e5d64`), on Ramon's go, **before** the v88-dependent steps (the Wyoming and Kentucky re-imports, the relabels and recomputes that need core `0d373728`);
    * steps 3 to 7 then follow, **together** as in `9e63a3d`.
* **Tasks already start on rev 90** (the latest revision) if you trigger a run, so **Oklahoma 2025+2026 can start now** (`07f2083`; `9e63a3d` batch 1), as you said. The core rollout is not needed for it: OK needs no v88 core fix. The loader's core `59dbdaa2` loads Oklahoma the same way.
* **The image still to be built is v89** (scrapers `b2aa844d`; `a0e5d64` step 1).

Tickets: OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
