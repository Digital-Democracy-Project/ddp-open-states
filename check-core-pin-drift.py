#!/usr/bin/env python3
"""
check-core-pin-drift.py -- fail when api-v3 and the scrapers image run different openstates-core commits (OPEN-579).

api-v3 imports its bill-version rules (stage, order, full text) from DDP's openstates-core fork, pinned by commit in
api-v3's ddp-openstates-core.txt (OPEN-538). The archiver in the scrapers image stores values computed by the same
rules (is_bill_version, diff_baseline_id). If the two run different core commits, api-v3's read-time values and the
stored values can contradict each other, and an older pin can break api-v3 outright (core eec94082: 47 test
failures). PLAN-state-specific-handling §4.4: one version of the rules on both sides.

Compares three commits, each a full 40-character SHA, and fails on any difference:

  pin        api-v3's ddp-openstates-core.txt (the checkout on this host; default <this repo>/api-v3/, or
             $API_V3_DIR): the commit in the fork archive URL.
  image      the core commit the live scrapers image was built from. The Dockerfile writes it to
             /opt/openstates-core/DDP_CORE_COMMIT before it deletes .git (OPEN-579; images before that, v60 and older,
             have no record). Either `--image <ref>` (read with `docker run`, so the image must be on this host: the
             Mac builds every tag) or `--image-core <sha>` (read elsewhere, e.g. from deploy-scrapers-image.sh's output
             or the task definition's image tag on the Mac; the EC2 host has no scrapers image). Which tag is live is the
             caller's to say, same convention as check-jurisdiction-drift.py's --live: this script makes no AWS call.
  installed  the openstates package installed in each api-v3 container (`--container`, repeatable; default
             ddp-openstates-api-1): pip's direct_url.json for the archive install carries the URL with the SHA. The
             version string cannot tell the fork from PyPI (both say 6.26.5), so a container with no direct_url.json
             (PyPI, or anything that is not an archive install of the fork) is drift too.

Usage (each host checks its own api-v3 container):
    python3 check-core-pin-drift.py --image 350941939790.dkr.ecr.us-east-1.amazonaws.com/ddp-scrapers:v61   # the Mac
    python3 check-core-pin-drift.py --image-core <40-hex sha>                                                 # EC2

Exit 0: all commits agree. Exit 1: drift (each disagreement names both commits). Exit 2: a source could not be read
(missing pin, no image record, container not running). A source that cannot be read is an ERROR, never a pass.
"""

import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONTAINER = "ddp-openstates-api-1"
IMAGE_RECORD = "/opt/openstates-core/DDP_CORE_COMMIT"  # written by the Dockerfile (OPEN-579)
FORK_ARCHIVE = re.compile(r"https://github\.com/Digital-Democracy-Project/openstates-core/archive/([0-9a-f]{40})\.tar\.gz")
PIN_LINE = re.compile(r"openstates\s*@\s*(\S+)")
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


def pin_commit(pin_path):
    """The commit in api-v3's ddp-openstates-core.txt (its one non-comment `openstates @ <archive url>` line)."""
    try:
        with open(pin_path) as fh:
            lines = [ln.strip() for ln in fh if ln.strip() and not ln.strip().startswith("#")]
    except OSError as exc:
        raise SourceError(f"pin: cannot read {pin_path}: {exc}")
    if len(lines) != 1:
        raise SourceError(f"pin: {pin_path} should have exactly one requirement line, found {len(lines)}")
    m = PIN_LINE.fullmatch(lines[0])
    sha = _fork_sha(m.group(1)) if m else None
    if not sha:
        raise SourceError(f"pin: {pin_path} is not an archive URL of the fork at a full commit: {lines[0]!r}")
    return sha


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


def run(pin_path, image, image_core, containers, out):
    found = []    # (label, sha)
    errors = []
    drift = []

    try:
        found.append(("pin " + pin_path, pin_commit(pin_path)))
    except SourceError as exc:
        errors.append(str(exc))

    if image and image_core:
        errors.append("give --image or --image-core, not both")
    elif image:
        try:
            found.append(("image " + image, image_commit(image)))
        except SourceError as exc:
            errors.append(str(exc))
    elif image_core:
        if FULL_SHA.fullmatch(image_core):
            found.append(("image (--image-core)", image_core))
        else:
            errors.append(f"--image-core must be a full 40-character commit, got {image_core!r}")
    else:
        errors.append("no scrapers image given: pass --image <ref> (the live tag) or --image-core <sha>")

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
                         f"archive URL: PyPI openstates, or not built from the pin)")
        else:
            found.append((label, sha))

    for label, sha in found:
        out.write(f"  {sha}  {label}\n")
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
        out.write("\napi-v3 and the scrapers image run different openstates-core commits. Bring them to one commit: "
                  "change api-v3's pin and rebuild both api-v3 copies, or ship a scrapers image from that commit.\n")
        return 1
    out.write(f"OK: api-v3's pin, the scrapers image and {len(containers)} api-v3 container(s) all run core "
              f"{found[0][1]}.\n")
    return 0


def main(argv, out=sys.stdout):
    parser = argparse.ArgumentParser(description="Compare api-v3's pinned openstates-core with the scrapers image's (OPEN-579).")
    api_v3_dir = os.environ.get("API_V3_DIR") or os.path.join(HERE, "api-v3")
    parser.add_argument("--pin", default=os.path.join(api_v3_dir, "ddp-openstates-core.txt"),
                        help="api-v3's ddp-openstates-core.txt (default: $API_V3_DIR or <this repo>/api-v3)")
    parser.add_argument("--image", help="the live scrapers image ref; its build record is read with `docker run`")
    parser.add_argument("--image-core", help="the live scrapers image's core commit (full SHA), when the image is not on this host")
    parser.add_argument("--container", action="append", default=None,
                        help=f"an api-v3 container to read (repeatable; default {DEFAULT_CONTAINER})")
    args = parser.parse_args(argv[1:])
    return run(args.pin, args.image, args.image_core, args.container or [DEFAULT_CONTAINER], out)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
