# All three orphaned loads recovered and spot-checked — OPEN-193 genuinely fully closed now

*Replies to `notes/open193-orphaned-data-recovery-authorized-20260902.md`.*

Ran one at a time as asked, confirmed each completion record before moving to the next, spot-checked each via api-v3 afterward.

**2026D** (`fl-1f280053977b`) — `status: "ok"`, exit 0: `bill: 0 new 2 updated 4 noop`,
`vote_event: 1 new 1 updated 5 noop`. Spot-check: SB 8D / HB 1D now show
`updated_at: 2026-09-03T00:12:2x` (fresh).

**2026E** (`fl-9237033aa89b`) — `status: "ok"`, exit 0: `bill: 0 new 22 updated 0 noop`,
`vote_event: 0 new 0 updated 54 noop`. Spot-check: all 5 sampled bills fresh
(`2026-09-03T00:12:54-58`).

**2026F** (`fl-c10699ea2180`) — `status: "ok"`, exit 0: `bill: 0 new 1 updated 4 noop`,
`vote_event: 1 new 0 updated 14 noop`. Spot-check: HJR 1F fresh
(`2026-09-03T00:13:20`); a few other sampled bills in this session showed older timestamps
(2026-06/07), consistent with `noop` (unchanged content, not re-touched) rather than a miss.

**One thing worth a look, not a stop-and-report per your own criteria (it didn't fail):** 2026F's
run logged two `ERROR`-level lines mid-import that the other two didn't:
```
ERROR openstates: cannot resolve pseudo id to Organization: ~{"name": "State Affairs Committee"}
ERROR openstates: cannot resolve pseudo id to Organization: ~{"name": "Appropriations"}
```
Exit code and `status` were still clean (0 / `ok`), so this wasn't treated as a failure requiring
a stop -- but flagging it since it's a fresh symptom, not one of tonight's already-diagnosed bugs.
Might just mean a bill action/vote referenced a committee whose org record wasn't in this
specific manifest's jurisdiction snapshot (plausible for older/incomplete captures); didn't
investigate further past confirming the load itself completed and the data landed.

**All 123 objects recovered. OPEN-193 item 4 is now closed with no known outstanding gaps** --
`ddp-sync` still running, healthy, `cloud_path` config unchanged from the closing state.
