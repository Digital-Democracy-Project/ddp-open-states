#!/usr/bin/env python3
"""
unmatched-voters.py — one jurisdiction's roll-call voter names that matched no one, as JSON (OPEN-855).

ddp-sync runs this after each state's load and alerts in #automation-errors when a state has a new unmatched name or
its unmatched share rose (`maybe_alert_unmatched_voters` in ddp-sync's pipelines/unmatched_voter_alert.py). The counting is
qa_primitives.unresolved_voter_names(): Stage 3's Gate 1 rule (a person-vote with voter_id NULL is unresolved), per
session and per printed name. This script only reads: its session is read-only.

Usage:
    DATABASE_URL=postgresql://... python3 unmatched-voters.py me

Prints one JSON object on stdout:
    {"state": "me", "sessions": {"132R1": {"total": 61234, "unresolved": 0}, ...},
     "names": [{"session": "132R1", "name": "PUGH of Portland", "count": 812, "accepted": false}, ...]}
`accepted` is true for a name on the state's `quality.accepted_unmatched_voters` in jurisdictions.yaml (known and
accepted for now); ddp-sync leaves those out of the alert.
Exit 0 on success, 2 when DATABASE_URL is missing or the database cannot be read (the message goes to stderr, never
the connection string).
"""
import argparse
import json
import os
import sys

from qa_primitives import MANIFEST_PATH, accepted_unmatched_names, unmatched_voters_result


accepted_names = accepted_unmatched_names  # OPEN-881: moved to qa_primitives, shared with cloud_unmatched_voters.py


def main(argv=None, connect=None, manifest_path=MANIFEST_PATH):
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("state", help="short jurisdiction code, e.g. me (us for Congress)")
    args = parser.parse_args(argv)
    state = args.state.lower()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("unmatched-voters.py: DATABASE_URL is not set", file=sys.stderr)
        return 2
    try:
        result = unmatched_voters_result(state, database_url, connect, manifest_path)
    except Exception as e:  # noqa: BLE001 -- any database failure is one exit code for the caller
        print(f"unmatched-voters.py: could not read {state}: {type(e).__name__}", file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
