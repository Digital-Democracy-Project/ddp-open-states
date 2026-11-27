# INTERIM (prod agent): v99 request `231f011` and update `d294c15` read; nothing run, waiting on Ramon's go and the Iowa re-import. 2026-11-27 (production host)

Read both notes in full. Status:
- **Nothing has been run** for v99: no EC2 api-v3 rebuild, no ddp-sync rebuild, no dry run, no re-import. Each step needs Ramon's go in my session naming the step.
- **Blocker I can see:** the Iowa full re-import (three sequential sessions) is still running, so ddp-sync cannot be rebuilt under the narrow restart rule until its locks clear. Estimated mid-morning UTC.
- **When I start:** I will re-run each gate on this host (core 1e138376 recorded in the image; the Virginia, North Carolina and Massachusetts file greps), check the pipeline locks, and stop on any shrinking, refused or errored document in a dry run.
- **Not mine now:** the Rhode Island LegBot sample moved to you (note `315764a`); Missouri and North Dakota samples are not started.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
