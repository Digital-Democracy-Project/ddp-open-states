#!/usr/bin/env python3
"""
Audit unique motion texts in the local OpenStates DB, grouped by jurisdiction.
Writes one markdown file per jurisdiction to ./motion-text-audit/.

Usage:
    python3 audit-motion-texts.py

Connects to the local OpenStates PostgreSQL on localhost:5433.
"""

import os
import psycopg2
import psycopg2.extras
from collections import defaultdict

DB = dict(
    host="localhost",
    port=5433,
    dbname="openstates",
    user="openstates",
    password="openstates_dev",
)

QUERY = """
SELECT
    j.name                              AS jurisdiction,
    ve.motion_text                      AS motion_text,
    ve.motion_classification            AS classification,
    COUNT(ve.id)                        AS vote_count,
    SUM(CASE WHEN ve.result = 'pass' THEN 1 ELSE 0 END) AS pass_count,
    SUM(CASE WHEN ve.result = 'fail' THEN 1 ELSE 0 END) AS fail_count
FROM opencivicdata_voteevent ve
JOIN opencivicdata_legislativesession ls ON ls.id = ve.legislative_session_id
JOIN opencivicdata_jurisdiction j        ON j.id  = ls.jurisdiction_id
GROUP BY j.name, ve.motion_text, ve.motion_classification
ORDER BY j.name, vote_count DESC, ve.motion_text
"""

OUT_DIR = os.path.join(os.path.dirname(__file__), "motion-text-audit")


def slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def classification_display(cls) -> str:
    if not cls:
        return "*(unclassified)*"
    return ", ".join(f"`{c}`" for c in cls)


def write_jurisdiction_file(jurisdiction: str, rows: list) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    filename = os.path.join(OUT_DIR, f"{slug(jurisdiction)}.md")

    total_votes = sum(r["vote_count"] for r in rows)
    classified = sum(r["vote_count"] for r in rows if r["classification"])
    pct = f"{100 * classified / total_votes:.0f}%" if total_votes else "0%"

    lines = [
        f"# Motion texts — {jurisdiction}",
        f"",
        f"**{len(rows)} unique motion texts** across {total_votes:,} vote events. "
        f"{classified:,} ({pct}) have an OpenStates classification set.",
        f"",
        f"| Motion text | Classification | Votes | Pass | Fail |",
        f"|---|---|---|---|---|",
    ]

    for r in rows:
        text = r["motion_text"].replace("|", "\\|").replace("\n", " ").strip()
        lines.append(
            f"| {text} "
            f"| {classification_display(r['classification'])} "
            f"| {r['vote_count']:,} "
            f"| {r['pass_count']:,} "
            f"| {r['fail_count']:,} |"
        )

    with open(filename, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"  wrote {filename}  ({len(rows)} motions, {total_votes:,} votes)")


def main():
    print(f"Connecting to OpenStates DB on localhost:{DB['port']}...")
    conn = psycopg2.connect(**DB)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    print("Running query...")
    cur.execute(QUERY)
    rows = cur.fetchall()
    conn.close()

    by_jurisdiction: dict[str, list] = defaultdict(list)
    for row in rows:
        by_jurisdiction[row["jurisdiction"]].append(row)

    print(f"\nWriting to {OUT_DIR}/\n")
    for jurisdiction, jrows in sorted(by_jurisdiction.items()):
        write_jurisdiction_file(jurisdiction, jrows)

    print(f"\nDone. {len(by_jurisdiction)} files written.")


if __name__ == "__main__":
    main()
