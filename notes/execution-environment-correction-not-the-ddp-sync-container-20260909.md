# Correction: I'm not running refresh-extraction from the ddp-sync container at all

*Replies to `notes/ddp-sync-dockerfile-poppler-fix-rebuild-20260909.md`.* Before anyone spends
more effort on this thread with the wrong premise: confirmed just now (`/.dockerenv` absent,
`/proc/1/cgroup` shows `init.scope` not a container cgroup) that this session runs directly on
the bare EC2 host, not inside any container. All the `refresh-extraction` runs so far used
`/opt/ddp-open-states/.venv/bin/os-text-extract` via `source activate.sh` — the dedicated
host-level OpenStates toolchain venv `PRIMITIVES.md` documents — not `ddp-sync`'s bundled
toolchain image.

So: **rebuilding `ddp-sync`'s container (ddp-sync#122) won't fix what I actually ran.** That
Dockerfile only affects things invoked from inside `ddp-sync`'s own container, which is a
separate execution path from this host's bare venv. The missing `pdftotext` binary is missing
from the bare host's OS packages, not from any container's filesystem — the ddp-open-states root
`Dockerfile` already has `poppler-utils` (added 2026-08-29, per your note), but that only affects
images built from it, not this host's own apt package state.

## What I think this means, but didn't act on

Installing `poppler-utils` on the bare host (`apt-get install poppler-utils`) is a normal,
permanent OS package change — not the kind of thing that "disappears on next rebuild" the way
live-patching a running container would. So Ramon's stated reasoning for preferring the
Dockerfile fix (avoid a fix that evaporates) may not actually apply to fixing *this* environment,
since there's no container here to rebuild away from under it. Still not doing this myself
without confirmation, since it's the same category of "changes this host's persistent state"
call I flagged before deciding not to.

## Question back

Two different things could both be true and aren't mutually exclusive:
1. `ddp-sync#122` is still worth merging/rebuilding regardless, for whatever *does* invoke
   `refresh-extraction`/`reextract` through that container (if anything does).
2. This host's bare venv toolchain — which is what actually produced the UT/WA numbers so far —
   still needs `poppler-utils` installed directly on the host OS to get a real baseline from
   *this* execution path.

Should I go ahead and `apt-get install poppler-utils` on this host directly, now that it's clear
that's a different (and non-evaporating) fix from the container one? Holding off until I hear
back either way.
