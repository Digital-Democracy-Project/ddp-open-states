#!/usr/bin/env python3
"""
check-core-pin-drift.py -- fail when api-v3, ddp-sync's cloud loader and the scrapers image run different openstates-core
commits (OPEN-579, SYNC-180).

api-v3 imports its bill-version rules (stage, order, full text) from DDP's openstates-core fork (OPEN-538). Both api-v3
and the scrapers image install the fork's main at build time (OPEN-586; api-v3 records the resolved commit in pip's
metadata, the image in DDP_CORE_COMMIT). The archiver in the scrapers image stores values computed by the same rules
(is_bill_version, diff_baseline_id). If the two were built at different moments they can carry different core commits,
and api-v3's read-time values and the stored values can contradict each other (an older core can also break api-v3
outright: core eec94082, 47 test failures). PLAN-state-specific-handling §4.4: one version of the rules on both sides.

Compares these commits, each a full 40-character SHA, and fails on any difference:

  image      the core commit the live scrapers image was built from. The Dockerfile writes it to
             /opt/openstates-core/DDP_CORE_COMMIT before it deletes .git (OPEN-579; images before that, v60 and older,
             have no record). Either `--image <ref>` (read with `docker run`, so the image must be on this host: the
             Mac builds every tag) or `--image-core <sha>` (read elsewhere, e.g. from deploy-scrapers-image.sh's output
             or the task definition's image tag on the Mac; the EC2 host has no scrapers image). Which tag is live is the
             caller's to say, same convention as check-jurisdiction-drift.py's --live: this script makes no AWS call.
  installed  the openstates package installed in each api-v3 container (`--container`, repeatable; default
             ddp-openstates-api-1): pip's direct_url.json for the archive install carries the URL with the SHA. api-v3's
             build installs the archive at DDP_CORE_SHA (the image's commit, passed in by refresh-api-v3.sh or the
             prod agent; `--print-image-core` prints it), so this is the core it actually runs. The
             version string cannot tell the fork from PyPI (both say 6.26.5), so a container with no direct_url.json
             (PyPI, or anything that is not an archive install of the fork) is drift too.
  loader     the core in each ddp-sync container (`--sync-container`, repeatable; none by default, because only EC2 runs
             ddp-sync in a container). Its cloud_loader.py imports scrapes into RDS with `os-update` from ddp-sync's own
             copy of core, not the image's (SYNC-180: it was found at v62's 44c3b8dc while v65 was live). ddp-sync's
             infrastructure/Dockerfile fetches core at DDP_CORE_SHA and writes the same /opt/openstates-core/DDP_CORE_COMMIT
             record as the image, read here with `docker exec ... cat`. A ddp-sync built before SYNC-180 has no record:
             an ERROR, never a pass.

Also reported, not compared: the openstates-scrapers commit in each ddp-sync container (SYNC-188). Its build fetches
scrapers at DDP_SCRAPERS_SHA and writes /opt/openstates-scrapers/DDP_SCRAPERS_COMMIT; the build itself fails when that
commit needs a newer core than DDP_CORE_SHA (check-scraper-imports.sh). The scrapers image keeps no such record, so there
is nothing here to compare it with; the release names the same commit as the image's (RUNBOOK). A ddp-sync built before
SYNC-188 has no record: an ERROR, never a pass.

Usage (each host checks its own api-v3 container):
    python3 check-core-pin-drift.py --image 350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v61   # the Mac
    python3 check-core-pin-drift.py --image-core <40-hex sha> --sync-container ddp-sync-ddp-sync-1                 # EC2

Exit 0: all commits agree. Exit 1: drift (each disagreement names both commits). Exit 2: a source could not be read
(no image record, container not running). A source that cannot be read is an ERROR, never a pass.
"""

import argparse
import json
import re
import subprocess
import sys

DEFAULT_CONTAINER = "ddp-openstates-api-1"
IMAGE_RECORD = "/opt/openstates-core/DDP_CORE_COMMIT"  # written by the Dockerfile (OPEN-579)
SCRAPERS_RECORD = "/opt/openstates-scrapers/DDP_SCRAPERS_COMMIT"  # written by ddp-sync's Dockerfile (SYNC-188)
FORK_ARCHIVE = re.compile(r"https://github\.com/Digital-Democracy-Project/openstates-core/archive/([0-9a-f]{40})\.tar\.gz")
FULL_SHA = re.compile(r"[0-9a-f]{40}")

# Run inside the api-v3 container (Python 3.9): print pip's direct_url.json for openstates, or nothing.
_READ_DIRECT_URL = ("import importlib.metadata as m; "
                    "print(m.distribution('openstates').read_text('direct_url.json') or '')")


class SourceError(Exception):
    """A source could not be read, or does not have the shape this checker expects."""


def _fork_sha(url):
    """The SHA when `url` is exactly the fork's archive URL at a full commit, else None (whole-string match)."""
    m = FORK_ARCHIVE.fullmatch(url) if isinstance(url, str) else None
    return m.group(1) if m else None


def _run(cmd):
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SourceError(f"`{' '.join(cmd)}` failed: {exc}")
    if res.returncode != 0:
        raise SourceError(f"`{' '.join(cmd)}` exited {res.returncode}: {(res.stderr or res.stdout).strip()[:300]}")
    return res.stdout


def image_commit(image):
    """The commit recorded in a scrapers image by its build."""
    try:
        out = _run(["docker", "run", "--rm", "--entrypoint", "cat", image, IMAGE_RECORD]).strip()
    except SourceError as exc:
        raise SourceError(f"image: {image} has no readable {IMAGE_RECORD} (images built before OPEN-579 have none; "
                          f"pass --image-core <sha> instead): {exc}")
    if not FULL_SHA.fullmatch(out):
        raise SourceError(f"image: {image}'s {IMAGE_RECORD} is not a full commit: {out!r}")
    return out


def installed_commit(container):
    """The fork commit the openstates package in an api-v3 container was installed from, or None (not the fork)."""
    out = _run(["docker", "exec", container, "python", "-c", _READ_DIRECT_URL]).strip()
    if not out:
        return None
    try:
        data = json.loads(out)
    except ValueError:
        raise SourceError(f"installed: {container}'s direct_url.json is not JSON: {out[:200]!r}")
    if not isinstance(data, dict):
        raise SourceError(f"installed: {container}'s direct_url.json is not an object: {out[:200]!r}")
    return _fork_sha(data.get("url"))


def loader_commit(container):
    """The core commit recorded in a ddp-sync container by its build (SYNC-180)."""
    try:
        out = _run(["docker", "exec", container, "cat", IMAGE_RECORD]).strip()
    except SourceError as exc:
        raise SourceError(f"loader: {container} has no readable {IMAGE_RECORD} (a ddp-sync built before SYNC-180 has "
                          f"none: rebuild it at the image's core): {exc}")
    if not FULL_SHA.fullmatch(out):
        raise SourceError(f"loader: {container}'s {IMAGE_RECORD} is not a full commit: {out!r}")
    return out


def loader_scrapers_commit(container):
    """The openstates-scrapers commit recorded in a ddp-sync container by its build (SYNC-188)."""
    try:
        out = _run(["docker", "exec", container, "cat", SCRAPERS_RECORD]).strip()
    except SourceError as exc:
        raise SourceError(f"loader: {container} has no readable {SCRAPERS_RECORD} (a ddp-sync built before SYNC-188 "
                          f"has none: rebuild it with DDP_SCRAPERS_SHA, the image's scrapers commit): {exc}")
    if not FULL_SHA.fullmatch(out):
        raise SourceError(f"loader: {container}'s {SCRAPERS_RECORD} is not a full commit: {out!r}")
    return out


def image_source(image, image_core):
    """(label, sha) of the live scrapers image's core, from exactly one of --image / --image-core."""
    if image and image_core:
        raise SourceError("give --image or --image-core, not both")
    if image:
        return "image " + image, image_commit(image)
    if image_core:
        if FULL_SHA.fullmatch(image_core):
            return "image (--image-core)", image_core
        raise SourceError(f"--image-core must be a full 40-character commit, got {image_core!r}")
    raise SourceError("no scrapers image given: pass --image <ref> (the live tag) or --image-core <sha>")


def run(image, image_core, containers, out, sync_containers=()):
    found = []    # (label, sha); the image first, so every drift line compares a container with the image
    reported = []  # (label, sha) of ddp-sync's scrapers: printed, not compared (SYNC-188)
    errors = []
    drift = []

    try:
        found.append(image_source(image, image_core))
    except SourceError as exc:
        errors.append(str(exc))

    if not containers:
        errors.append("no api-v3 container given")
    for container in containers:
        label = "installed in " + container
        try:
            sha = installed_commit(container)
        except SourceError as exc:
            errors.append(f"installed: {exc}")
            continue
        if sha is None:
            drift.append(f"{label} is not an archive install of the fork at a commit (no direct_url.json with a fork "
                         f"archive URL: PyPI openstates, or built before OPEN-586 from something else)")
        else:
            found.append((label, sha))

    for container in sync_containers:
        try:
            found.append(("ddp-sync loader in " + container, loader_commit(container)))
        except SourceError as exc:
            errors.append(str(exc))
        try:
            reported.append(("ddp-sync scrapers in " + container, loader_scrapers_commit(container)))
        except SourceError as exc:
            errors.append(str(exc))

    for label, sha in found:
        out.write(f"  {sha}  {label}\n")
    for label, sha in reported:
        out.write(f"  {sha}  {label} (openstates-scrapers, reported only)\n")
    if found:
        ref_label, ref_sha = found[0]
        for label, sha in found[1:]:
            if sha != ref_sha:
                drift.append(f"{label} is {sha}, but {ref_label} is {ref_sha}")

    for line in drift:
        out.write(f"DRIFT {line}\n")
    for message in errors:
        out.write(f"ERROR {message}\n")
    if errors:
        return 2
    if drift:
        out.write("\napi-v3, ddp-sync and the scrapers image must run one openstates-core commit. Bring them to it: "
                  "rebuild both api-v3 copies at the live image's core (refresh-api-v3.sh does; on EC2 set DDP_CORE_SHA), "
                  "and rebuild ddp-sync on EC2 with DDP_CORE_SHA set to the same commit (and DDP_SCRAPERS_SHA to the "
                  "image's scrapers commit, SYNC-188). "
                  "If the image named here is not the live one, name the live one. Release order: the image, then any "
                  "stored recompute, then api-v3 and ddp-sync.\n")
        return 1
    loaders = f" and {len(sync_containers)} ddp-sync container(s)" if sync_containers else ""
    out.write(f"OK: the scrapers image and {len(containers)} api-v3 container(s){loaders} all run core "
              f"{found[0][1]}.\n")
    return 0


def main(argv, out=sys.stdout):
    parser = argparse.ArgumentParser(description="Compare the openstates-core commit in each api-v3 container (and each "
                                                 "ddp-sync container given) with the scrapers image's (OPEN-579, "
                                                 "OPEN-586, SYNC-180).")
    parser.add_argument("--image", help="the live scrapers image ref; its build record is read with `docker run`")
    parser.add_argument("--image-core", help="the live scrapers image's core commit (full SHA), when the image is not on this host")
    parser.add_argument("--container", action="append", default=None,
                        help=f"an api-v3 container to read (repeatable; default {DEFAULT_CONTAINER})")
    parser.add_argument("--sync-container", action="append", default=None,
                        help="a ddp-sync container whose cloud loader's core to read (repeatable; none by default, SYNC-180)")
    parser.add_argument("--print-image-core", action="store_true",
                        help="print the image's core commit and exit (refresh-api-v3.sh builds api-v3 at it, OPEN-586)")
    args = parser.parse_args(argv[1:])
    if args.print_image_core:
        try:
            out.write(image_source(args.image, args.image_core)[1] + "\n")
        except SourceError as exc:
            out.write(f"ERROR {exc}\n")
            return 2
        return 0
    return run(args.image, args.image_core, args.container or [DEFAULT_CONTAINER], out, args.sync_container or [])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
