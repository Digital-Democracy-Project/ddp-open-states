#!/usr/bin/env python3
"""
unmatched-voters.py — one jurisdiction's roll-call voter names that matched no one, as JSON (OPEN-855).

ddp-sync runs this after each state's load and alerts in #automation-errors when a state has a new unmatched name or
its unmatched share rose (`_maybe_alert_unmatched_voters` in ddp-sync's openstates_scrape.py). The counting is
qa_primitives.unresolved_voter_names(): Stage 3's Gate 1 rule (a person-vote with voter_id NULL is unresolved), per
session and per printed name. This script only reads: its session is read-only.

Usage:
    DATABASE_URL=postgresql://... python3 unmatched-voters.py me

Prints one JSON object on stdout:
    {"state": "me", "sessions": {"132R1": {"total": 61234, "unresolved": 0}, ...},
     "names": [{"session": "132R1", "name": "PUGH of Portland", "count": 812}, ...]}
Exit 0 on success, 2 when DATABASE_URL is missing or the database cannot be read (the message goes to stderr, never
the connection string).
"""
import argparse
import json
import os
import sys

from qa_primitives import unresolved_voter_names


def main(argv=None, connect=None):
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("state", help="short jurisdiction code, e.g. me (us for Congress)")
    args = parser.parse_args(argv)
    state = args.state.lower()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("unmatched-voters.py: DATABASE_URL is not set", file=sys.stderr)
        return 2
    if connect is None:
        import psycopg2

        connect = psycopg2.connect
    try:
        conn = connect(database_url)
        try:
            conn.set_session(readonly=True)
            result = unresolved_voter_names(conn, state)
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001 -- any database failure is one exit code for the caller
        print(f"unmatched-voters.py: could not read {state}: {type(e).__name__}", file=sys.stderr)
        return 2
    print(json.dumps({"state": state, **result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
