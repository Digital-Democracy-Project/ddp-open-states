"""
qa_primitives.py — shared QA/onboarding database primitives (OPEN-445).

verify-jurisdiction (the Stage 0 onboarding probe) and quality_check.py (the Stage 3 QA gate) both
need a few small, stable DB queries scoped by jurisdiction. Before OPEN-445 they existed only in
verify-jurisdiction, which has no .py extension and can't be `import`ed by name -- so this module
is the one plain-importable home for them. verify-jurisdiction now imports from here instead of
keeping its own copies of ocd_jurisdiction_id()/count_people_loaded(); quality_check.py's own
_ocd_id() is a thin alias of ocd_jurisdiction_id() below, so there is exactly one implementation of
each rule rather than two that can quietly drift apart.

find_db_vote_key_collisions() and attribution_resolution_rates() are new in OPEN-445 -- Stage
3-only queries over the full imported dataset, with no Stage 0 sibling (Stage 0's gate I samples a
bounded dry-scrape instead, since nothing is imported yet at that point). They live here because
this is already "the module for shared QA primitives scoped by jurisdiction," not because anything
else reuses them yet.
"""


# DC is a district and the five territories are territories in the ids the scrapers create in the database,
# not states (OPEN-472: the state-style id counted zero people for them even after they loaded).
_NON_STATE_DIVISIONS = {
    "as": "territory:as",
    "dc": "district:dc",
    "gu": "territory:gu",
    "mp": "territory:mp",
    "pr": "territory:pr",
    "vi": "territory:vi",
}


def ocd_jurisdiction_id(st):
    """Short code -> the OCD jurisdiction id string used throughout the local DB."""
    if st == "us":
        return "ocd-jurisdiction/country:us/government"
    return f"ocd-jurisdiction/country:us/{_NON_STATE_DIVISIONS.get(st, f'state:{st}')}/government"


def count_people_loaded(conn, st):
    """Distinct people with a membership in one of this jurisdiction's organizations. Zero means no
    qualifying people are present (usually `os-people to-database <st>` has not run); a positive
    count says some are present, not that the roster is complete (the parity gate checks that).

    OPEN-446's original gate H query, moved here (OPEN-445) so quality_check.py's Stage 3 "people
    loaded" gate re-asserts the exact same invariant gate H already checks before the first
    import, instead of a second, possibly-drifting copy of the same query."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT count(DISTINCT m.person_id)
        FROM opencivicdata_membership m
        JOIN opencivicdata_organization o ON o.id = m.organization_id
        WHERE o.jurisdiction_id = %s AND m.person_id IS NOT NULL
        """,
        (ocd_jurisdiction_id(st),),
    )
    return cur.fetchone()[0]


def find_db_vote_key_collisions(conn, st):
    """OPEN-445 Gate 2 (unique vote keys): every imported VoteEvent.dedupe_key for this
    jurisdiction, across every session actually in the database -- not a bounded dry-scrape sample
    (that's verify-jurisdiction's gate I / compare_vote_keys(), OPEN-397). Same rule, different
    source: the importer matches a keyed vote on the key alone (PRIMITIVES.md, OPEN-252/397), so a
    repeated key across more than one (session, bill) pair means the importer silently collapsed
    two different votes into one row, or would fail a future load that tried to write fresh rows
    for them.

    Returns (collisions, n_sessions_with_votes):
      - collisions: {dedupe_key: [(session_identifier, bill_identifier), ...]} for every key that
        repeats across more than one (session, bill) pair.
      - n_sessions_with_votes: the number of distinct legislative sessions that have at least one
        vote event. The gate itself decides "not applicable" when this is <= 1 (the ticket's "for
        any state with more than one session" scoping) -- this function always runs the full query
        (one indexed scan) rather than hiding that decision here.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ve.dedupe_key, ls.identifier, b.identifier
        FROM opencivicdata_voteevent ve
        JOIN opencivicdata_legislativesession ls ON ls.id = ve.legislative_session_id
        LEFT JOIN opencivicdata_bill b ON b.id = ve.bill_id
        WHERE ls.jurisdiction_id = %s AND ve.dedupe_key IS NOT NULL
        """,
        (ocd_jurisdiction_id(st),),
    )
    seen = {}
    sessions_with_votes = set()
    for dedupe_key, session_identifier, bill_identifier in cur.fetchall():
        sessions_with_votes.add(session_identifier)
        seen.setdefault(dedupe_key, set()).add((session_identifier, bill_identifier))
    collisions = {key: sorted(where) for key, where in seen.items() if len(where) > 1}
    return collisions, len(sessions_with_votes)


def attribution_resolution_rates(conn, st):
    """OPEN-445 Gate 1 (attribution resolution): what share of this jurisdiction's imported vote
    rows and person-sponsorships actually resolved to a person, not just a name.

    A vote row is unresolved when voter_id IS NULL, even when voter_name is set -- a name with no
    resolved person is exactly the NC failure mode this ticket exists to catch. A sponsorship is
    scoped to entity_type = 'person' rows only: BillSponsorship also covers organization entities
    (committees, etc.), which have no person to resolve and would otherwise water down the measured
    rate with rows this gate was never meant to judge.

    Returns {'votes': {'total': int, 'unresolved': int}, 'sponsorships': {'total': int,
    'unresolved': int}}. Either total can be 0 for a jurisdiction with no votes or no
    person-sponsorships imported yet -- the caller decides what an empty population means
    (not-applicable), not this function.

    OPEN-261 ("Add a probe/QA gate for unresolved voter attribution") named this gap first and, as
    of OPEN-445, is still open with no implementation anywhere in this repo. OPEN-445 builds the
    real measurement here because its own acceptance criteria require a working, numeric gate
    end-to-end; OPEN-261 should import this function rather than duplicate it.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT count(*), count(*) FILTER (WHERE pv.voter_id IS NULL)
        FROM opencivicdata_personvote pv
        JOIN opencivicdata_voteevent ve ON ve.id = pv.vote_event_id
        JOIN opencivicdata_legislativesession ls ON ls.id = ve.legislative_session_id
        WHERE ls.jurisdiction_id = %s
        """,
        (ocd_jurisdiction_id(st),),
    )
    votes_total, votes_unresolved = cur.fetchone()

    cur.execute(
        """
        SELECT count(*), count(*) FILTER (WHERE bs.person_id IS NULL)
        FROM opencivicdata_billsponsorship bs
        JOIN opencivicdata_bill b ON b.id = bs.bill_id
        JOIN opencivicdata_legislativesession ls ON ls.id = b.legislative_session_id
        WHERE ls.jurisdiction_id = %s AND bs.entity_type = 'person'
        """,
        (ocd_jurisdiction_id(st),),
    )
    sponsorships_total, sponsorships_unresolved = cur.fetchone()

    return {
        "votes": {"total": votes_total, "unresolved": votes_unresolved},
        "sponsorships": {"total": sponsorships_total, "unresolved": sponsorships_unresolved},
    }
