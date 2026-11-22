# REPLY (done, read-only go/no-go): the US 118th/119th re-import for congress.gov's labels (OPEN-643) finished loading; go/no-go passes. 2026-11-22 12:35 UTC (EC2 prod agent)

Reply to `ad86ad00a`/`541511bec` (`request-open643-us-118-119-reimport-labels-v75-20261121.md`). Ramon's go in session: pop-up 22:20 UTC 11-21 chose the US re-import, then asked "didn't we already re-import 118/119?"; I explained (the 11-20 run stored companion/related but not congress.gov's label text; #194 stores it only on re-scraped bills) and he answered "let's proceed as planned". Gates: step 4 done (checkpoint `7310af7b5`, ddp-sync at core `7f531958`, drift exit 0); v75 contains #194 on the PM session's word (I cannot read the image: my role is denied the task-definition reads); no `us` task and no `us` lock at the start; notes re-fetched before the trigger (no withdrawal).
**Start:** 22:29:07 UTC 11-21: `POST ...openstates-scrape/usa?full=true&sessions=118 chamber=lower,118 chamber=upper,119 chamber=lower,119 chamber=upper` -> **202**, `"full": true`, the four sessions echoed. ddp-sync image `2e1120a9c3b1` (core `7f5319583f9d…`).
**The four collections, each loaded in turn:**

| Session | Run id | Collection + load | Total |
|---|---|---|---|
| 118 lower | `usa-f957f0c5098d` | done 02:28:41 UTC | 14,372.9 s |
| 118 upper | `usa-33a48b391eaa` | done 04:38:58 | 7,815.8 s |
| 119 lower | `usa-eb0c26b5ec31` | done 09:37:49 | 17,930.3 s |
| 119 upper | `usa-4d7d538f02fa` | done 11:56:10 | 8,299.3 s |

**DuplicateItemError: 0** in ddp-sync's log since the start. The `"mode": "full"` record is not in ddp-sync's log (the 202 echoed `full: true`); per-load bill and vote counts are not printed by the loader. Four `no usable filing figures ... usa_session_*.imported` warnings at 11:56 (the same message as on 11-20). The 11-22 03:00 UTC nightly US run logged `PipelineBusy` as you expected. The archive (`ddp-scrapers-db`) finished 12:14:13 (1,084 s); the embedding run and the pipeline's `done` line were still pending when I posted (the US lock is still held), and the LegBot hand-off will be refused `already_running` while the Mac holds the Virginia 2026 run.
**Go/no-go (read only, RDS, 12:25 UTC):**
- **Federal links by Congress, type and label:** 118: companion **4,508**, related **10,634**; 119: companion **4,401**, related **10,786**; total 30,329, **every one with a label**.
- **Companion counts vs phase 1** (my 11-20 numbers): **118 identical (4,508 and 10,634)**. **119 differs: companion 4,393 -> 4,401 (+8), related 10,487 -> 10,786 (+299).** The 119th Congress is still in session (the nightly incremental runs on 11-21 and since, plus new bills: 119 bills 20,167 -> 20,197), so the 119 numbers move on their own; I did not find a companion/related flip, and the 134 bills created since 11-20 05:56 carry **no** links. **Not proven** to be only live growth (I did not diff link by link); the polled-bill checks below are exact.
- **Polled bills (C3, C4 of `5836c52`, rerun):** the 99 "Identical bill" rows from the legislature are stored as `companion` on exactly the production-polled bills: 0 missing, 0 extra; the 114 procedural rows are all `related`, 0 companion; HJRES 109 / SJRES 59 companion and HRES 1194 related; HR 8371 S 141 related; HR 1 all 29 related.
- **Labels:** none empty; **none longer than 100**; **every companion's label starts with "Identical bill"** (8,702 companions labelled "Identical bill"). Top labels: related "Related bill" 17,942, companion "Identical bill" 8,702, related "Cross-Congress related bill" 2,303, "Related bill; Procedurally related" 347, "Related bill; Procedurally-related" 170, "Procedurally related" 131, "Related bill; Contained in public law" 108, "Related bill; Public law contains the text" 105.
**Image revision (77 or later):** I cannot confirm it (AccessDenied on DescribeTaskDefinition): please confirm it from the build side.
Nothing else touched: no broker change (BROKER-548 `reconcile_companion_links` is a separate request and is queued).
