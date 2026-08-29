# OPEN-200: containerizes cloud_collector.py (OPEN-201) plus the real os-update toolchain --
# not a standalone stand-in. OPEN-200's own scope calls this out explicitly: "The real unit is
# os-update <state> --scrape bills, carrying pupa/OCD, Django models and a hard pydantic<2
# pin ... not a standalone program."
#
# Mirrors activate.sh's documented rebuild recipe for the toolchain venv exactly:
#   /usr/bin/python3 -m venv .venv && .venv/bin/pip install 'pip<24.1' \
#     && .venv/bin/pip install --no-deps -r requirements-openstates.txt
# plus an editable install of openstates-core from DDP's fork (requirements-openstates.txt's
# own header explains why openstates itself is never pinned in that file) and openstates-
# scrapers on PYTHONPATH -- checked against activate.sh 2026-08-28: that package is NOT pip-
# installed at all in the real venv (`pip show openstates-scrapers` there returns nothing).
# activate.sh instead points PYTHONPATH straight at its `scrapers/` subdirectory. Worth
# knowing before "fixing" this: an editable pip install of that package fails outright here --
# its pyproject.toml declares the pre-poetry-core `requires = ["poetry>=0.12"]` backend, which
# has no native PEP 660 editable-install support, and pip's setup.py-develop fallback then
# collides with modern setuptools' flat-layout package-discovery strictness (two top-level
# dirs, `scrapers` and `scrapers_next`). That is a real, separate, pre-existing packaging
# defect in the fork worth its own ticket -- not something to route around by patching
# packaging metadata in this PR. PYTHONPATH is not a workaround for it; it is simply how this
# pipeline has always run that package.
#
# Two-stage build: the builder stage needs git and compilers for any package requirements-
# openstates.txt has no prebuilt wheel for; the final image carries only the venv and this
# repo's own runner, per the fargate draft's "no local filesystem assumptions" / small-image
# requirements.

FROM python:3.9-slim AS builder

# git: clones the two forks below. build-essential/libxml2-dev/libxslt-dev/libssl-dev: in case
# a package in requirements-openstates.txt (lxml, cryptography) has no prebuilt wheel for this
# platform and falls back to a source build -- cheap to include, expensive to discover missing.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git build-essential libxml2-dev libxslt1-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements-openstates.txt .
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir 'pip<24.1' \
    && /opt/venv/bin/pip install --no-cache-dir --no-deps -r requirements-openstates.txt

# Cloned via a BuildKit secret (a GitHub PAT) so the credential is never written into an image
# layer -- the fargate draft's "no credentials baked into the image" requirement, applied to
# the build step too, not just the runtime container. Usage:
#   DOCKER_BUILDKIT=1 docker build --secret id=github_token,env=GITHUB_PERSONAL_ACCESS_TOKEN .
#
# `main`, not a "local-patches" branch: requirements-openstates.txt's own header comment refers
# to one, but checked 2026-08-28 against both live DDP forks -- neither has ever had a branch
# by that name, and the checkout actually installed from is on `main`. That comment is stale;
# worth a one-line fix there too, noted rather than silently carried forward here.
# Cloned straight to /opt, the SAME path they live at in the final image below -- not /build.
# pm-review caught two real bugs in the earlier version of this step, both from cloning to a
# builder-only path and copying the checkout (not just the installed package) across stages:
#   1. A PEP 660 editable install of openstates-core records an absolute path back to its
#      source checkout (a .pth/finder, not a copy of the code). If that path is /build/... and
#      the final image only has /opt/..., the import silently breaks in the stage that matters.
#      Cloning to the final path directly makes the recorded path correct by construction,
#      rather than trusting a path rewrite that has to be remembered forever.
#   2. `git clone` records the token-bearing HTTPS URL in .git/config. The secret mount keeps
#      the token out of the RUN layer itself, but the CHECKOUT it produces still contains it --
#      and the previous version of this file copied the whole checkout, .git included, into
#      the final image. Removing .git right after the install (still in the builder stage, so
#      it never occupies a final-image layer) is what actually keeps the token out, not the
#      secret mount alone.
ARG OPENSTATES_CORE_REF=main
ARG OPENSTATES_SCRAPERS_REF=main
RUN --mount=type=secret,id=github_token \
    TOKEN=$(cat /run/secrets/github_token) && \
    git clone --branch "$OPENSTATES_CORE_REF" --depth 1 \
        "https://x-access-token:${TOKEN}@github.com/Digital-Democracy-Project/openstates-core.git" \
        /opt/openstates-core && \
    git clone --branch "$OPENSTATES_SCRAPERS_REF" --depth 1 \
        "https://x-access-token:${TOKEN}@github.com/Digital-Democracy-Project/openstates-scrapers.git" \
        /opt/openstates-scrapers && \
    rm -rf /opt/openstates-core/.git /opt/openstates-scrapers/.git

# Editable install for openstates-core only (so DDP's patches take effect, exactly as this
# repo's own venv does it -- see requirements-openstates.txt's header). Verified 2026-08-28:
# builds and installs cleanly, `os-update --help` runs from it immediately afterward -- and,
# after this fix, verified again from the FINAL stage specifically (see PR), since that is the
# copy that matters and the earlier verification only checked the builder stage.
RUN /opt/venv/bin/pip install --no-cache-dir --no-deps -e /opt/openstates-core


FROM python:3.9-slim

RUN groupadd --gid 1000 scraper && useradd --uid 1000 --gid scraper --shell /bin/bash --create-home scraper

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/openstates-core /opt/openstates-core
COPY --from=builder /opt/openstates-scrapers /opt/openstates-scrapers

WORKDIR /app
COPY cloud_collector.py import-summary.sh docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

ENV PATH="/opt/venv/bin:$PATH"
# Not pip-installed -- see the builder stage's note. This is the same PYTHONPATH activate.sh
# sets for the real pipeline, pointed at the cloned checkout's own scrapers/ subdirectory.
ENV PYTHONPATH="/opt/openstates-scrapers/scrapers"
ENV PYTHONUNBUFFERED=1

USER scraper

# SIGTERM handling per the draft's Phase 1: exec form + no shell wrapper, so a container stop
# signals cloud_collector.py's own process directly rather than a shell that swallows it.
ENTRYPOINT ["./docker-entrypoint.sh"]
