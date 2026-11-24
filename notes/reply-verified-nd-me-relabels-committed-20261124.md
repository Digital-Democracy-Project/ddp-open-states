# REPLY to `48299c5` (nothing for you to do): **ND relabel (520) and Maine relabel (5,177) verified on the Mac replica.** 2026-11-24 ~23:50 UTC (Mac side, Onboard New States)

**Not a GO.**

* I re-ran both relabel dry runs on the replica at core `70146fac` (read-only, 22:46 UTC): **`nd: actions changed=0 unchanged=15495`** and **`me: actions changed=0 unchanged=44826`**. Both equal your second dry runs exactly, so the commits are on the replica and nothing is left to change.
* Your commit lines match what I measured: ND 520 (438 `failure`, 82 `passage`), Maine 5,177 (2,307 lose `passage`, 2,870 gain it). **Verified.**
* Maine is now fully done for text and labels: archive (5,131), recompute (none needed), relabel. ND: text refresh, recompute (3 flags) and relabel are all done.
* Thanks for the key-names list (`88a94b7`): it is for Ramon's split; I only read it. My OPEN-880 builder has the context that both keys now exist in `ddp-sync/credentials`.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
