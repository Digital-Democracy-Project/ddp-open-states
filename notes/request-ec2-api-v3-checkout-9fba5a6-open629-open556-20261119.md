# REQUEST (Ramon's go, given 2026-11-19 in the PM session's terminal): rebuild EC2's api-v3 with its checkout pulled to api-v3 main `9fba5a6`, core unchanged at `c983ae68`. It brings OPEN-629 (oldest-action order) and OPEN-556 (chamber names) live. 2026-11-19 (Mac side)

**Ramon, 2026-11-19 (relayed by the PM session):** yes to this rebuild.

**Why:**
* Your checkpoint `47e3abd` rebuilt at core `c983ae68`, but EC2's api-v3 checkout stayed at `7160cbc`. So two merged api-v3 changes are not live there:
  * **OPEN-629** (api-v3 #73): `GET /bills?sort=latest_action_asc` across all states, for Explore's "Oldest action" sort. NEXT-256 / ddp-next #306 waits on it.
  * **OPEN-556** (api-v3 #71): `/ddp/enrollment` serves each state's chamber names and the one-house flag.
* **What's in `7160cbc..9fba5a6`** (checked on the Mac, 11-19): only #73 (`848cfec`, `5e95313`) and #71 (`0c0c965`, `6ee5ced`, `9fba5a6`). That is 5 files (`api/bills.py`, `api/ddp_enrollment.py` and their tests).
* **api-v3 #72 (OPEN-557) is NOT merged** (head `b6eceb47`, open), is not in that range, and must not ride along.
* **The Mac's api-v3 has served both since 22:06 UTC 11-18** (rebuilt from `9fba5a6`). The checks below are what it answers.

## What I need from you
1. **Gates (read only):**
   * **OPEN-556's release condition** (its ticket, comments 21186 and 21464): the manifest copy that EC2's api-v3 reads must carry a `chambers:` block for **every** state, as added by ddp-open-states #410 `27dfda01`. Otherwise `/ddp/enrollment` answers 503 and the broker loses its state list.
     * Check that the host's ddp-open-states checkout contains `27dfda01`.
     * Check that the manifest file api-v3 mounts has `chambers:` once per state (17 states today, including NM). The count of `^  chambers:` lines should equal the count of state entries.
     * **If any state lacks it: stop and report.**
   * The api-v3 checkout is clean at `7160cbc`. After `git pull --ff-only origin main` it must be exactly **`9fba5a6`**. Anything else, or a non-fast-forward: stop.
   * No ddp-sync loader or os-update lines in the last 10 minutes. healthz 200 before.
   * Not during 05:00 to 07:00 UTC.
2. **Rebuild:** your `47e3abd` method.
   * Tag the running image `ddp-openstates-api:pre-9fba5a6` for rollback.
   * Build with `DDP_CORE_SHA=c983ae68599e94494a94edc23d576b483922302e` (`docker-compose.rds.yml`).
   * `up -d --no-deps api` only.
3. **Checks after:**
   * healthz 200;
   * `check-core-pin-drift.py --image-core c983ae68599e94494a94edc23d576b483922302e --container ddp-openstates-api-1` exits 0;
   * **OPEN-556:** `GET /ddp/enrollment` returns 17 jurisdictions, each with `chambers`:
     * `va` → `{"unicameral": false, "upper": "Senate", "lower": "House of Delegates"}`;
     * `ne` → `{"unicameral": true, "upper": "Legislature", "lower": null}`;
     * `nv` → `{"unicameral": false, "upper": "Senate", "lower": "Assembly"}`.

     Also through the broker's web container, as in `a630172`: 200, 17 jurisdictions.
   * **OPEN-629:** `GET /bills?sort=latest_action_asc&per_page=3`, with no jurisdiction, answers **200** (before #73 it was refused for all states), oldest first. On the Mac today: US SRES 4, SRES 6, SRES 9, each dated 2023-01-03.
   * ddp-sync log: 0 Tracebacks in the minutes after.
4. **Rollback:** retag `:pre-9fba5a6` as `:local` and recreate api only. The checkout can stay at `9fba5a6`.
5. Report with a `checkpoint-` note.

## Not authorized
* api-v3 #72 (OPEN-557).
* Any core change.
* The NM recompute commit (that is `47e3abd`'s own GO).
* Any manifest edit.
* Any other service.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
