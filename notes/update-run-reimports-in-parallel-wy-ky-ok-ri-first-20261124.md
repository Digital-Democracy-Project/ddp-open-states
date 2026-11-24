# UPDATE (not a GO) to `e30bb8e` step 4, `a0e5d64` step 3 and `07f2083` (B): **start the re-imports together, each its own Fargate task, each with its own pass/fail line.** Wyoming, Kentucky, Oklahoma and Rhode Island first. 2026-11-24 ~20:00 UTC (Mac side, Onboard New States)

**Not a GO.** Ramon's direction (2026-11-24, /ask-me, via the PM session): "run them all in parallel on fargate and tell the session agent to stop forcing scrapers to run in sequence." Please confirm it with him in your session, as for every relayed answer.

## What changes
* **"One heavy load at a time" (`e30bb8e` step 4, `a0e5d64` step 3, and my other notes) is removed.** I had carried it over from the earlier requests without evidence of a limit. Each state is its own run, and a failure in one **does not stop** the others.
* **Verification is no longer a gate between starts.** I verify each state on the Mac replica when it finishes and post "verified" or a stop for that state. Nothing waits for my note.
* **Each state keeps its own pass/fail lines** (those in `e30bb8e` step 4 and `a0e5d64` step 3). A failure is "stop and report **that state**"; no retry.
* **One exception: a systemic failure.** If two or more states fail with the **same** error (a certificate error, an import error in the loader, an RDS or S3 error), **stop starting further runs** and report. Don't retry.

## The real constraints, in plain words, with the evidence
1. **One run per state.** A state's own lock (`ddp:pipeline_lock:<st>`) and its S3 import lock (per source) mean a second run of the **same** state is refused (409 or "another import holds the lock"). They don't affect other states. **A state's two sessions run one after the other inside its one request.**
2. **Slots.** ddp-sync's cloud-scrape pool holds **32** (`CLOUD_SCRAPE_SLOTS`; SYNC-187, live since `85c8888`; a waiting run logs `cloud_scrape_waiting_for_slot`). Starting up to 32 together is allowed.
3. **What is tested.** On 11-23 about 16 states were running or queued together (`85c8888`'s note), on the old limit of **8** at once. So **8 at once is demonstrated**; between 9 and 32 isn't.
4. **Where the load happens.** Collection runs on **Fargate**, one task per state, so it adds nothing to the EC2 host. The **load** into RDS runs on the **EC2 ddp-sync host** (`cloud_loader.py` as a subprocess) after collection. Loads are **short next to collection**: MS collected 98 minutes and loaded 8; MD collected 107 and loaded 7; ID loaded in 2. So starting all together **staggers the loads on its own** (collections end at different times), and overlapping loads are rare. **I have no measured safe number for simultaneous loads on that host or on RDS.**
5. **Restarts.** A ddp-sync restart while any run is **loading** leaves an orphan 24 h S3 import lock for that state (Oklahoma and Iowa on 11-23). **Parallel runs make "nothing is loading" rarer, so no restart or rollout while any run is in its load phase** (your own rule since `aa0bf45`; SYNC-189 now releases a resumed run's own lock, which narrows this).

**So: start all of a batch together.** Please report, for the first batch, the **load average and memory on the EC2 host** at the busiest moment (and RDS CPU if you can read it), and the highest number of runs at once. If you see trouble (a loader failing from memory, RDS errors), stop starting more and report. I'd rather learn the real limit from that than guess one.

## The order, batch by batch
* **Batch 1: Wyoming, Kentucky, Oklahoma, Rhode Island first** (Broker Upgrades needs their re-imported data for their scorecard rules). Start them together:

| State | What | Image / prerequisite |
|---|---|---|
| **WY** | `wy?full=true&sessions=2026` (`e30bb8e` 4a) | v88; core `0d373728` has #150 and #160 |
| **KY** | `ky?full=true&sessions=2026RS` (`e30bb8e` 4b) | v88; **after the KY people load** (`e30bb8e` step 3: Lewis C) |
| **OK** | `ok?full=true&sessions=2025,2026` (`07f2083`, lock expired) | v88 or v86, whichever is live; **both sessions** |
| **RI** | **no re-import.** Its verified data (`f83ade8`) is current; what it needs is `remove-stale-documents ri` (3,011), then its relabel and recompute dry runs (`e30bb8e` steps 5 to 7) | core `0d373728` |

* **Batch 2, together with batch 1 or straight after: everything else queued.**
    * HI `2026` (once, v88) and NM `2026` (`a1c833f`);
    * IA `2026,2026s1`, then `2025` as its own run (`07f2083`; its two requests are for the same state, so they follow each other);
    * ME's v86 run (`me-98110acf6911`) finishes on its own.
* **On v89** (`a0e5d64` step 3): **MO, NV and AL, together** after v89's Step 2 backfills.
    * Nevada's **apply** (Step 2) goes before the Nevada re-import only to keep the broker order. The re-import writes the same result.
* **Dependencies that remain, because the data needs them, not because of sequence:**
    * KY's people load before KY's re-import;
    * a stale-document removal before that state's recompute;
    * a relabel or recompute only after that state's re-import or its removal is done;
    * v89's Nevada apply and image before broker `0116`.

## Relabels, recomputes and the guarded backfills
* They write stored rows, so each keeps **its own dry run, its own go and its own second go**.
* **They can still be requested for all states together:** each state's dry run runs as soon as its prerequisite is met, and all the dry-run numbers come to Ramon in one report. Nothing about them changes in `e30bb8e` steps 5 to 7 or `a0e5d64` step 2, except that no state waits for another.

## Not authorized
Unchanged from `e30bb8e` and `a0e5d64`. Also: a second run of the same state, Hawaii or Wyoming twice, and Missouri before v89.

Tickets: OPEN-146; OPEN-662, 667, 666, 665 (WY, KY, OK, RI) first.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
