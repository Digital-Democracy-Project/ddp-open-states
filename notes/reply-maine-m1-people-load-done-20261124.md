# Reply (2026-11-24 03:05 UTC): Maine M1 (`a92378e`) people load DONE; step 4 for Maryland waits for the core rollout

Ramon, in my session (pop-up 11-24: "Maine people load only (can run now)" and "Core eb197d74 rollout + v85 plan"). People pulled `d1acd229fc` to **`05d7e4cca4`** (fast-forward; MD #49's Harlan files came with the pull, **not loaded**). **`os-people`, `me` only, `--safe` then real:** `processed 623 person files, 0 created, 17 updated` both times (**expected 0 and 17: match**), exit 0, no "went missing" or retirement line; **188 current Maine legislators** read back from RDS.
**Not done:** Maryland's people load (`0940569` step 4 says any time after step 1, the core rollout; it waits until then), v85 steps, the core rollout (after the nightlies; api-v3 not 05:00-07:00 UTC). Read and noted: `4389222` (v86 for Washington's nightly), `85a8950` (v85 = rev 87/db 14 at core eb197d74; v86's core `59dbdaa2`), `a1c833fb` (NM re-import on v86): all wait for Ramon's go and their images; if v86 is built before the core rollout I will ask Ramon whether to roll out `59dbdaa2` directly instead of `eb197d74`.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
