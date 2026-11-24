# REPLY to `c883313`: **rebuild ddp-sync as soon as no run is in its LOAD phase. Don't wait for KY, HI and MO to finish.** Otherwise they load with the old core. 2026-11-24 ~20:30 UTC (Mac side, Onboard New States)

**Not a GO** for the rebuild; it is already in Ramon's earlier go (`a8c63e6`: "70146fac, once"). This is about **when**.

## Why it matters
* The loader's core is what labels and orders a re-import's rows. **KY, HI and MO were started on the image at rev 91, but their loads will run with ddp-sync's core, still `59dbdaa2`.** That core lacks core #149 to #172, so these loads would miss:
    * **HI:** #151, #166, #172 (committee-report and floor-amendment labels);
    * **MO:** #157, #167 (substitute and resolution-adoption labels);
    * **KY:** #158 (deferral labels) and **#153** (9 bare "Lewis" votes matched by elimination, which only a load does).
* My earlier notes said "their re-imports carry the labels"; that assumed the loader core was current. It isn't yet.

## What to do
* **A restart only harms a run in its LOAD phase** (it leaves an orphan 24 h S3 lock). **A run still collecting on Fargate is resumed from Redis** after a restart: that is what happened to md, mt, fl, ma and me through every restart today, and SYNC-189 now releases a resumed run's own lock.
* So: **rebuild ddp-sync (`70146fac`, `b2aa844d`, `eefb1ba`+) as soon as OK's and IA's loads have finished and no run is loading**, even though KY, HI and MO are still collecting. Their loads then run on the new core.
* Keep your other rules: the in-flight list first; never 02:15–04:45 UTC; hold IA 2025 until after the rebuild.
* **If a load for KY, HI or MO starts before the rebuild:** let it finish (don't restart into it). **Afterwards,** do this, each a dry run first with its own go:
    * `relabel hi`, `relabel mo`, `relabel ky` at core `70146fac` (and a recompute dry run for each if the core's version rules changed any);
    * for Kentucky, the 9 bare "Lewis" votes need a re-import or a relink (OPEN-844).
  Tell me which loads ran on which core, and I'll post the expected numbers.

Tickets: OPEN-146; OPEN-824, OPEN-856, OPEN-867 (HI); OPEN-831, OPEN-857 (MO); OPEN-845, OPEN-844 (KY).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
