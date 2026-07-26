#!/usr/bin/env python3
"""
Audit unresolved (voter_id IS NULL) rows in opencivicdata_personvote, grouped by
jurisdiction and legislative session.

For every distinct unresolved voter_name, also reports a "candidate count": how many
currently-known people in that jurisdiction/chamber match the name by the same
exact/alias/family-name lookup opencivicdata's resolve_person() uses (name, other_names,
family_name -- case-insensitive, no fuzzy matching, no membership date-range filter).
That count distinguishes:
  - 0 candidates  -> true "no match" (format mismatch, missing alias, brand-new name)
  - 1 candidate   -> a match exists but resolve_person() still failed -- almost always a
                     membership start/end-date scoping mismatch, since this query doesn't
                     apply that filter
  - 2+ candidates -> ambiguous, same-surname collision within the jurisdiction/chamber

This is read-only and does not modify any data. See
notes/votebot-unknown-votes-architecture-20260726.md (OPEN-2) for the design rationale
behind auditing before touching resolve_person() or backfilling.

Usage:
    python3 audit-unresolved-votes.py
    DATABASE_URL=postgresql://... python3 audit-unresolved-votes.py

Environment:
    DATABASE_URL   Local openstates DB
                   (default: postgresql://openstates:openstates_dev@localhost:5433/openstates)
"""

import os
import re
from collections import defaultdict

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://openstates:openstates_dev@localhost:5433/openstates",
)

OUT_DIR = os.path.join(os.path.dirname(__file__), "unresolved-votes-audit")

SUMMARY_QUERY = """
SELECT
    j.name                                                AS jurisdiction,
    ls.identifier                                         AS session,
    COUNT(pv.id)                                          AS total_votes,
    SUM(CASE WHEN pv.voter_id IS NULL THEN 1 ELSE 0 END)  AS unresolved_votes
FROM opencivicdata_personvote pv
JOIN opencivicdata_voteevent ve          ON ve.id = pv.vote_event_id
JOIN opencivicdata_legislativesession ls ON ls.id = ve.legislative_session_id
JOIN opencivicdata_jurisdiction j        ON j.id  = ls.jurisdiction_id
GROUP BY j.name, ls.identifier
ORDER BY j.name, unresolved_votes DESC
"""

UNRESOLVED_NAMES_QUERY = """
SELECT
    j.name             AS jurisdiction,
    j.id               AS jurisdiction_id,
    o.classification   AS chamber,
    pv.voter_name       AS voter_name,
    COUNT(*)            AS vote_count
FROM opencivicdata_personvote pv
JOIN opencivicdata_voteevent ve          ON ve.id = pv.vote_event_id
JOIN opencivicdata_legislativesession ls ON ls.id = ve.legislative_session_id
JOIN opencivicdata_jurisdiction j        ON j.id  = ls.jurisdiction_id
JOIN opencivicdata_organization o        ON o.id  = ve.organization_id
WHERE pv.voter_id IS NULL
GROUP BY j.name, j.id, o.classification, pv.voter_name
ORDER BY j.name, vote_count DESC
"""

# Mirrors resolve_person()'s name/other_names/family_name spec (base.py:585-593),
# scoped to jurisdiction + chamber (base.py:596-604), minus the membership
# start/end-date filter -- deliberately, so a single candidate here that still failed
# resolution points at a date-range mismatch rather than a name-format mismatch.
CANDIDATE_COUNT_QUERY = """
SELECT COUNT(DISTINCT p.id) AS candidate_count
FROM opencivicdata_person p
JOIN opencivicdata_membership m   ON m.person_id = p.id
JOIN opencivicdata_organization o ON o.id = m.organization_id
WHERE o.jurisdiction_id = %s
  AND o.classification = %s
  AND (
      p.name ILIKE %s
      OR p.family_name ILIKE %s
      OR EXISTS (
          SELECT 1 FROM opencivicdata_personname pn
          WHERE pn.person_id = p.id AND pn.name ILIKE %s
      )
  )
"""


def normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip()


def verdict(candidate_count: int) -> str:
    if candidate_count == 0:
        return "no match"
    if candidate_count == 1:
        return "1 candidate, still unresolved -- check date/scope"
    return f"ambiguous ({candidate_count} candidates)"


def slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def write_jurisdiction_file(jurisdiction: str, session_rows: list, name_rows: list) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    filename = os.path.join(OUT_DIR, f"{slug(jurisdiction)}.md")

    total_votes = sum(r["total_votes"] for r in session_rows)
    total_unresolved = sum(r["unresolved_votes"] for r in session_rows)
    pct = f"{100 * total_unresolved / total_votes:.1f}%" if total_votes else "0.0%"

    lines = [
        f"# Unresolved votes — {jurisdiction}",
        "",
        f"**{total_unresolved:,} of {total_votes:,} vote events ({pct}) have no resolved "
        f"`voter`.**",
        "",
        "## By session",
        "",
        "| Session | Total votes | Unresolved | % |",
        "|---|---|---|---|",
    ]
    for r in session_rows:
        s_pct = (
            f"{100 * r['unresolved_votes'] / r['total_votes']:.1f}%"
            if r["total_votes"]
            else "0.0%"
        )
        lines.append(
            f"| {r['session']} | {r['total_votes']:,} | {r['unresolved_votes']:,} | {s_pct} |"
        )

    lines += [
        "",
        "## Unresolved voter names",
        "",
        "| Voter name | Chamber | Votes | Candidates | Verdict |",
        "|---|---|---|---|---|",
    ]
    for r in name_rows:
        name = r["voter_name"].replace("|", "\\|").strip()
        lines.append(
            f"| {name} | {r['chamber'] or '?'} | {r['vote_count']:,} "
            f"| {r['candidate_count']} | {r['verdict']} |"
        )

    with open(filename, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"  wrote {filename}  ({len(name_rows)} unresolved names, {total_unresolved:,} votes)")


def main():
    print(f"Connecting to {DATABASE_URL}...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    print("Running summary query...")
    cur.execute(SUMMARY_QUERY)
    summary_rows = cur.fetchall()

    print("Running unresolved-names query...")
    cur.execute(UNRESOLVED_NAMES_QUERY)
    name_rows = cur.fetchall()

    print(
        f"Scoring candidate counts for {len(name_rows)} unresolved names "
        "(this may take a moment)..."
    )
    for row in name_rows:
        pattern = normalize(row["voter_name"])
        cur.execute(
            CANDIDATE_COUNT_QUERY,
            (row["jurisdiction_id"], row["chamber"], pattern, pattern, pattern),
        )
        row["candidate_count"] = cur.fetchone()["candidate_count"]
        row["verdict"] = verdict(row["candidate_count"])

    conn.close()

    sessions_by_jurisdiction = defaultdict(list)
    for row in summary_rows:
        sessions_by_jurisdiction[row["jurisdiction"]].append(row)

    names_by_jurisdiction = defaultdict(list)
    for row in name_rows:
        names_by_jurisdiction[row["jurisdiction"]].append(row)

    total_votes = sum(r["total_votes"] for r in summary_rows)
    total_unresolved = sum(r["unresolved_votes"] for r in summary_rows)

    print(f"\nWriting to {OUT_DIR}/\n")
    for jurisdiction in sorted(sessions_by_jurisdiction):
        write_jurisdiction_file(
            jurisdiction,
            sessions_by_jurisdiction[jurisdiction],
            names_by_jurisdiction.get(jurisdiction, []),
        )

    overall_pct = f"{100 * total_unresolved / total_votes:.1f}%" if total_votes else "0.0%"
    print(
        f"\nDone. {len(sessions_by_jurisdiction)} jurisdiction files written. "
        f"Overall: {total_unresolved:,}/{total_votes:,} votes unresolved ({overall_pct})."
    )


if __name__ == "__main__":
    main()
