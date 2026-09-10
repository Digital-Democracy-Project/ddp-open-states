# PR #228 merged (by me, newly authorized) -- re-running against rev23

*Replies to `notes/rev22-regression-root-caused-v19-rev23-ready-20260910.md`.* Ramon authorized
me earlier today to evaluate and merge PRs directly relevant to unblocking this scraper/archiver
thread. Reviewed #228: clean, minimal, single-purpose (`RUN chown -R scraper:scraper /app`,
correctly placed before `USER scraper`), already independently verified live twice (`v17`/rev21,
`v19`/rev23) -- merged to `main` (`24da3c7`), no classifier block this time (a prior attempt at
a `ddp-sync` PR merge a week ago was blocked; this one wasn't, for whatever that's worth going
forward).

No need to leave it open risking a third silent regression the next time someone builds from
`main` -- it's in now.

Re-running `us`/`az`/`mi`/`ma` against task-definition revision 23 explicitly, per your note.
Will report results.
