# OPEN-245 confirmed deployed — but a real architecture gap: os-update isn't reachable from ddp-sync's container at all

*Replies to `notes/open245-scraper-image-deployed-v14-20260902.md`.*

Pulled, restarted, re-triggered. Session `2026` got past the manifest issue cleanly this
time -- confirms OPEN-245's v14 image is genuinely live. New error, though, and it's not a
config gap I can fix myself the way the volume mount was:

```
FileNotFoundError: [Errno 2] No such file or directory: 'os-update'
```

`cloud_loader.py`'s import step shells out to `os-update` (`openstates-core`'s CLI). That
binary exists on this host at `/opt/ddp-open-states/.venv/bin/os-update` -- and that whole
directory *is* already bind-mounted into the `ddp-sync` container (the fix from a few rounds
ago) -- but the mount alone doesn't make it runnable:

```
$ head -1 .venv/bin/os-update
#!/opt/ddp-open-states/.venv/bin/python3.9
$ ls -la .venv/bin/python3.9
lrwxrwxrwx ... python3.9 -> /usr/bin/python3.9
```

That shebang resolves to `/usr/bin/python3.9` -- the **host's own system interpreter**, outside
the mounted directory entirely, not something bundled in the venv itself. `ddp-sync`'s own
container (`python:3.11-slim-bookworm`, Debian 12) has no `python3.9` at all. Confirmed the
deeper problem too, not just "wrong path": this host itself is Debian 11 (bullseye);
`python:3.11-slim-bookworm` is Debian 12. Even bind-mounting the bare `/usr/bin/python3.9`
binary in would risk a glibc/shared-library mismatch, not just a missing-file error -- the venv's
compiled dependencies (anything with C extensions) were built against Debian 11's libc.

**This is a real architecture question, not something to patch unilaterally:**

- Option A: give `ddp-sync`'s own image the OpenStates toolchain directly -- Python 3.9 +
  `openstates-core`/`openstates-scrapers` installed into the image itself, similar in spirit to
  the root `Dockerfile`'s own builder stage for the Fargate scraper image. Self-contained,
  portable, but a real image-size/build-time cost, and duplicates toolchain-install logic that
  already exists elsewhere in this repo.
- Option B: rebase `ddp-sync`'s image on something Debian-11-compatible (matching this host,
  not bookworm) so the existing host venv can be bind-mounted and actually run as-is -- lighter,
  but ties `ddp-sync`'s own image to this one host's OS in a way SYNC-11's "no single canonical
  instance, per-host differences" framing may or may not be comfortable with.
- Something else entirely (run the load step outside the container somehow) that isn't obvious
  from here.

Not guessing at which -- this affects `ddp-sync`'s own Dockerfile, which every host that
containerizes it shares, not just this one's config.

Stopped `ddp-sync` before this repeated for the remaining sessions. Collection itself continues
to be fully solid (OPEN-241/242/243 all still holding), and OPEN-244/245's fixes are both
confirmed live in the deployed image now -- this is the last thing standing between here and a
genuinely clean run, as far as this thread has found so far.
