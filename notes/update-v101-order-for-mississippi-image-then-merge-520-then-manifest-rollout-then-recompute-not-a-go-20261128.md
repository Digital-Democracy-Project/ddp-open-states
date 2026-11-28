# UPDATE (adds to my request `3ab2aa9`; still NOT a GO): **the order for Mississippi's cleaner is: image first, then the manifest pull request is merged, then the manifest rollout, then the recompute.** 2026-11-28 (Mac side, Onboard New States)

## What I need from you (a change to Part 3 of `3ab2aa9`, Mississippi only)
1. **Do not run `recompute-diff-order ms` as a commit, and do not expect the Mississippi manifest to name the cleaner yet.** Today `main`'s manifest says Mississippi's `quality.diff_cleaner` is `none`; the change to `clean_ms_text` is ddp-open-states pull request #520 and it is **held unmerged on purpose** until you report the new image live. A manifest rollout takes the whole of `main`'s manifest, so a merged #520 would ride along with any other manifest rollout, possibly before the image with core #194 is live.
2. **The order:** (a) the image with core `6bc462ff` or newer is live (your Part 1 and 2 reads); (b) I tell you in a note that #520 is merged (the PM and the reviewer do that once your note shows the image live); (c) the manifest rollout (pull first, then the script, dry run first, as for Alabama); (d) `recompute-diff-order ms --dry-run` with the cleaner, then a commit on Ramon's go. Until (c), run only the refresh dry run (`refresh-extraction ms`) from Part 3; the recompute dry run in `3ab2aa9` would read the cleaner as `none`, so treat its lines as informational, not as the expected ones.
3. Everything else in `3ab2aa9` stands.

## Not authorized
As in `3ab2aa9`; in particular any commit, and any manifest rollout before the image is live.

Tickets: OPEN-949, OPEN-950, OPEN-669; OPEN-146.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
