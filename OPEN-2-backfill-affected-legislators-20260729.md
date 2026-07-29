# OPEN-2 backfill: legislators whose votes will be affected

Generated 2026-07-29, immediately before running `backfill-vote-person-resolution.py` for real against production Postgres. Lists every U.S. Congress legislator with at least one vote record that currently shows no party (`voter_id IS NULL`) and will be resolved by the backfill, plus how many of their votes get fixed.

**Legislators affected: 220**  
**Total votes to be resolved: 144,340**  
**Votes that will remain unresolved (no matching identifier found): 3,133** — mostly former members whose ID doesn't match anyone currently on file; expected, not a bug.

| Name | Party | Chamber | District | Votes resolved |
|---|---|---|---|---|
| Mark Amodei | Republican | House | NV-2 | 518 |
| Tammy Baldwin | Democratic | Senate | Wisconsin | 387 |
| Nanette Barragán | Democratic | House | CA-44 | 1,148 |
| John Barrasso | Republican | Senate | Wyoming | 387 |
| Aaron Bean | Republican | House | FL-4 | 1,148 |
| Michael Bennet | Democratic | Senate | Colorado | 387 |
| Andy Biggs | Republican | House | AZ-5 | 518 |
| Sheri Biggs | Republican | House | SC-3 | 518 |
| Dan Bishop | Republican | House | NC-8 | 630 |
| Sanford Bishop | Democratic | House | GA-2 | 630 |
| Marsha Blackburn | Republican | Senate | Tennessee | 387 |
| Richard Blumenthal | Democratic | Senate | Connecticut | 387 |
| Cory Booker | Democratic | Senate | New Jersey | 387 |
| John Boozman | Republican | Senate | Arkansas | 387 |
| Brendan Boyle | Democratic | House | PA-2 | 1,148 |
| Mike Braun | Republican | Senate | Indiana | 133 |
| Katie Britt | Republican | Senate | Alabama | 387 |
| Sherrod Brown | Democratic | Senate | Ohio | 133 |
| Ted Budd | Republican | Senate | North Carolina | 387 |
| Maria Cantwell | Democratic | Senate | Washington | 387 |
| Shelley Moore Capito | Republican | Senate | West Virginia | 387 |
| Ben Cardin | Democratic | Senate | Maryland | 133 |
| Tom Carper | Democratic | Senate | Delaware | 133 |
| Buddy Carter | Republican | House | GA-1 | 1,148 |
| John Carter | Republican | House | TX-31 | 1,148 |
| Troy Carter | Democratic | House | LA-2 | 1,148 |
| Bob Casey | Democratic | Senate | Pennsylvania | 133 |
| Bill Cassidy | Republican | Senate | Louisiana | 387 |
| Kathy Castor | Democratic | House | FL-14 | 1,148 |
| Joaquin Castro | Democratic | House | TX-20 | 1,148 |
| Katherine Clark | Democratic | House | MA-5 | 1,148 |
| Yvette Clarke | Democratic | House | NY-9 | 1,148 |
| Susan Collins | Republican | Senate | Maine | 387 |
| Chris Coons | Democratic | Senate | Delaware | 387 |
| John Cornyn | Republican | Senate | Texas | 387 |
| Catherine Cortez Masto | Democratic | Senate | Nevada | 387 |
| Tom Cotton | Republican | Senate | Arkansas | 387 |
| Kevin Cramer | Republican | Senate | North Dakota | 387 |
| Mike Crapo | Republican | Senate | Idaho | 387 |
| Ted Cruz | Republican | Senate | Texas | 387 |
| Tony Cárdenas | Democratic | House | CA-29 | 630 |
| Steve Daines | Republican | Senate | Montana | 387 |
| Sharice Davids | Democratic | House | KS-3 | 1,148 |
| Danny Davis | Democratic | House | IL-7 | 1,148 |
| Don Davis | Democratic | House | NC-1 | 1,148 |
| Madeleine Dean | Democratic | House | PA-4 | 1,148 |
| Tammy Duckworth | Democratic | Senate | Illinois | 387 |
| Neal Dunn | Republican | House | FL-2 | 1,148 |
| Dick Durbin | Democratic | Senate | Illinois | 387 |
| Joni Ernst | Republican | Senate | Iowa | 387 |
| Dwight Evans | Democratic | House | PA-3 | 518 |
| Gabe Evans | Republican | House | CO-8 | 518 |
| Dianne Feinstein | Democratic | Senate | California | 35 |
| John Fetterman | Democratic | Senate | Pennsylvania | 387 |
| Deb Fischer | Republican | Senate | Nebraska | 387 |
| Lois Frankel | Democratic | House | FL-22 | 1,148 |
| Scott Franklin | Republican | House | FL-18 | 1,148 |
| Mike Garcia | Republican | House | CA-27 | 630 |
| Robert Garcia | Democratic | House | CA-42 | 1,148 |
| Sylvia Garcia | Democratic | House | TX-29 | 1,148 |
| Chuy García | Democratic | House | IL-4 | 1,148 |
| Brandon Gill | Republican | House | TX-26 | 518 |
| Kirsten Gillibrand | Democratic | Senate | New York | 387 |
| Carlos Giménez | Republican | House | FL-28 | 1,148 |
| Marie Gluesenkamp Perez | Democratic | House | WA-3 | 1,148 |
| Jared Golden | Democratic | House | ME-2 | 1,148 |
| Craig Goldman | Republican | House | TX-12 | 518 |
| Dan Goldman | Democratic | House | NY-10 | 1,148 |
| Tony Gonzales | Republican | House | TX-23 | 1,011 |
| Vicente Gonzalez | Democratic | House | TX-34 | 520 |
| Bob Good | Republican | House | VA-5 | 630 |
| Lance Gooden | Republican | House | TX-5 | 630 |
| Lindsey Graham | Republican | Senate | South Carolina | 384 |
| Chuck Grassley | Republican | Senate | Iowa | 387 |
| Garret Graves | Republican | House | LA-6 | 630 |
| Sam Graves | Republican | House | MO-6 | 630 |
| Al Green | Democratic | House | TX-9 | 1,148 |
| Mark Green | Republican | House | TN-7 | 804 |
| Marjorie Taylor Greene | Republican | House | GA-14 | 913 |
| Bill Hagerty | Republican | Senate | Tennessee | 387 |
| Abe Hamadeh | Republican | House | AZ-8 | 518 |
| Josh Harder | Democratic | House | CA-9 | 1,148 |
| Andy Harris | Republican | House | MD-1 | 518 |
| Mark Harris | Republican | House | NC-8 | 518 |
| Maggie Hassan | Democratic | Senate | New Hampshire | 387 |
| Josh Hawley | Republican | Senate | Missouri | 387 |
| Martin Heinrich | Democratic | Senate | New Mexico | 387 |
| George Helmy | Democratic | Senate | New Jersey | 7 |
| Kevin Hern | Republican | House | OK-1 | 518 |
| John Hickenlooper | Democratic | Senate | Colorado | 387 |
| Brian Higgins | Democratic | House | NY-26 | 295 |
| Clay Higgins | Republican | House | LA-3 | 1,148 |
| French Hill | Republican | House | AR-2 | 518 |
| Mazie Hirono | Democratic | Senate | Hawaii | 387 |
| John Hoeven | Republican | Senate | North Dakota | 387 |
| Val Hoyle | Democratic | House | OR-4 | 1,148 |
| Jeff Hurd | Republican | House | CO-3 | 518 |
| Cindy Hyde-Smith | Republican | Senate | Mississippi | 387 |
| Jeff Jackson | Democratic | House | NC-14 | 630 |
| Jonathan Jackson | Democratic | House | IL-1 | 1,148 |
| Ronny Jackson | Republican | House | TX-13 | 1,148 |
| Bill Johnson | Republican | House | OH-6 | 285 |
| Dusty Johnson | Republican | House | SD-AL | 1,148 |
| Hank Johnson | Democratic | House | GA-4 | 1,148 |
| Julie Johnson | Democratic | House | TX-32 | 518 |
| Mike Johnson | Republican | House | LA-4 | 935 |
| Ron Johnson | Republican | Senate | Wisconsin | 387 |
| Dave Joyce | Republican | House | OH-14 | 1,148 |
| John Joyce | Republican | House | PA-13 | 1,148 |
| Tim Kaine | Democratic | Senate | Virginia | 387 |
| Sydney Kamlager | Democratic | House | CA-37 | 1,148 |
| Tom Kean | Republican | House | NJ-7 | 630 |
| Mark Kelly | Democratic | Senate | Arizona | 387 |
| Mike Kelly | Republican | House | PA-16 | 1,148 |
| Robin Kelly | Democratic | House | IL-2 | 1,148 |
| Trent Kelly | Republican | House | MS-1 | 1,148 |
| John Neely Kennedy | Republican | Senate | Louisiana | 387 |
| Mike Kennedy | Republican | House | UT-3 | 518 |
| Tim Kennedy | Democratic | House | NY-26 | 518 |
| Jen Kiggans | Republican | House | VA-2 | 1,148 |
| Kevin Kiley | Independent | House | CA-3 | 518 |
| Andy Kim | Democratic | Senate | New Jersey | 867 |
| Young Kim | Republican | House | CA-40 | 630 |
| Angus King | Independent | Senate | Maine | 387 |
| Amy Klobuchar | Democratic | Senate | Minnesota | 387 |
| James Lankford | Republican | Senate | Oklahoma | 387 |
| Rick Larsen | Democratic | House | WA-2 | 1,148 |
| John Larson | Democratic | House | CT-1 | 1,148 |
| Barbara Lee | Democratic | House | CA-12 | 630 |
| Laurel Lee | Republican | House | FL-15 | 1,148 |
| Mike Lee | Republican | Senate | Utah | 387 |
| Summer Lee | Democratic | House | PA-12 | 1,148 |
| Susie Lee | Democratic | House | NV-3 | 1,148 |
| Ben Ray Luján | Democratic | Senate | New Mexico | 387 |
| Cynthia Lummis | Republican | Senate | Wyoming | 387 |
| Joe Manchin | Independent | Senate | West Virginia | 133 |
| Ed Markey | Democratic | Senate | Massachusetts | 387 |
| Roger Marshall | Republican | Senate | Kansas | 387 |
| Mitch McConnell | Republican | Senate | Kentucky | 387 |
| Cathy McMorris Rodgers | Republican | House | WA-5 | 630 |
| Analilia Mejía | Democratic | House | NJ-11 | 124 |
| Jeff Merkley | Democratic | Senate | Oregon | 387 |
| Carol Miller | Republican | House | WV-1 | 1,148 |
| Mary Miller | Republican | House | IL-15 | 1,148 |
| Max Miller | Republican | House | OH-7 | 1,148 |
| Barry Moore | Republican | House | AL-1 | 1,148 |
| Blake Moore | Republican | House | UT-1 | 1,148 |
| Gwen Moore | Democratic | House | WI-4 | 1,148 |
| Riley Moore | Republican | House | WV-2 | 518 |
| Tim Moore | Republican | House | NC-14 | 518 |
| Jerry Moran | Republican | Senate | Kansas | 387 |
| Markwayne Mullin | Republican | Senate | Oklahoma | 338 |
| Lisa Murkowski | Republican | Senate | Alaska | 387 |
| Chris Murphy | Democratic | Senate | Connecticut | 387 |
| Patty Murray | Democratic | Senate | Washington | 387 |
| Zach Nunn | Republican | House | IA-3 | 1,148 |
| Jon Ossoff | Democratic | Senate | Georgia | 387 |
| Alex Padilla | Democratic | Senate | California | 387 |
| Rand Paul | Republican | Senate | Kentucky | 387 |
| Gary Peters | Democratic | Senate | Michigan | 387 |
| Jack Reed | Democratic | Senate | Rhode Island | 387 |
| Pete Ricketts | Republican | Senate | Nebraska | 387 |
| Josh Riley | Democratic | House | NY-19 | 518 |
| Jim Risch | Republican | Senate | Idaho | 387 |
| Hal Rogers | Republican | House | KY-5 | 1,148 |
| Mike Rogers | Republican | House | AL-3 | 1,148 |
| Mitt Romney | Republican | Senate | Utah | 133 |
| Jacky Rosen | Democratic | Senate | Nevada | 387 |
| Mike Rounds | Republican | Senate | South Dakota | 387 |
| Marco Rubio | Republican | Senate | Florida | 137 |
| Bernie Sanders | Independent | Senate | Vermont | 387 |
| Brian Schatz | Democratic | Senate | Hawaii | 387 |
| Adam Schiff | Democratic | Senate | California | 262 |
| Eric Schmitt | Republican | Senate | Missouri | 387 |
| Chuck Schumer | Democratic | Senate | New York | 387 |
| Austin Scott | Republican | House | GA-8 | 1,148 |
| Bobby Scott | Democratic | House | VA-3 | 1,148 |
| David Scott | Democratic | House | GA-13 | 1,030 |
| Rick Scott | Republican | Senate | Florida | 387 |
| Tim Scott | Republican | Senate | South Carolina | 387 |
| Jeanne Shaheen | Democratic | Senate | New Hampshire | 387 |
| Kyrsten Sinema | Independent | Senate | Arizona | 133 |
| Adam Smith | Democratic | House | WA-9 | 1,148 |
| Adrian Smith | Republican | House | NE-3 | 1,148 |
| Chris Smith | Republican | House | NJ-4 | 1,148 |
| Jason Smith | Republican | House | MO-8 | 1,148 |
| Tina Smith | Democratic | Senate | Minnesota | 387 |
| Debbie Stabenow | Democratic | Senate | Michigan | 133 |
| Dan Sullivan | Republican | Senate | Alaska | 387 |
| Linda Sánchez | Democratic | House | CA-38 | 1,148 |
| Jon Tester | Democratic | Senate | Montana | 133 |
| Bennie Thompson | Democratic | House | MS-2 | 1,148 |
| G.T. Thompson | Republican | House | PA-15 | 1,148 |
| Mike Thompson | Democratic | House | CA-4 | 1,148 |
| John Thune | Republican | Senate | South Dakota | 387 |
| Thom Tillis | Republican | Senate | North Carolina | 387 |
| Norma Torres | Democratic | House | CA-35 | 1,148 |
| Ritchie Torres | Democratic | House | NY-15 | 1,148 |
| Tommy Tuberville | Republican | Senate | Alabama | 387 |
| Mike Turner | Republican | House | OH-10 | 518 |
| Sylvester Turner | Democratic | House | TX-18 | 52 |
| Chris Van Hollen | Democratic | Senate | Maryland | 387 |
| JD Vance | Republican | Senate | Ohio | 134 |
| Nydia Velázquez | Democratic | House | NY-7 | 1,148 |
| Michael Waltz | Republican | House | FL-6 | 15 |
| Mark Warner | Democratic | Senate | Virginia | 387 |
| Raphael Warnock | Democratic | Senate | Georgia | 387 |
| Elizabeth Warren | Democratic | Senate | Massachusetts | 387 |
| Randy Weber | Republican | House | TX-14 | 1,148 |
| Daniel Webster | Republican | House | FL-11 | 1,148 |
| Peter Welch | Democratic | Senate | Vermont | 387 |
| Sheldon Whitehouse | Democratic | Senate | Rhode Island | 387 |
| Roger Wicker | Republican | Senate | Mississippi | 387 |
| Brandon Williams | Republican | House | NY-22 | 630 |
| Nikema Williams | Democratic | House | GA-5 | 1,148 |
| Roger Williams | Republican | House | TX-25 | 1,148 |
| Frederica Wilson | Democratic | House | FL-24 | 1,148 |
| Joe Wilson | Republican | House | SC-2 | 1,148 |
| Ron Wyden | Democratic | Senate | Oregon | 387 |
| Todd Young | Republican | Senate | Indiana | 387 |

## By party

| Party | Legislators | Votes resolved |
|---|---|---|
| Democratic | 102 | 69,595 |
| Republican | 113 | 73,187 |
| Independent | 5 | 1,558 |

## By chamber

| Chamber | Legislators | Votes resolved |
|---|---|---|
| House | 118 | 108,338 |
| Senate | 102 | 36,002 |

## Follow-up: post-run verification (2026-07-29)

Ran the backfill for real, then verified it three separate ways before trusting the result.

**1. It worked.** Re-ran `backfill-vote-person-resolution.py --dry-run` immediately after the
real run: it now reports **0 newly-resolvable rows, 3,133 still unresolvable** — the exact
number predicted above, confirming every row that could be fixed was fixed, with nothing left
half-done. Also spot-checked the original bug-report bill directly against the live replica
(HR 8646, "On Passage" vote): **0 of 430 votes unresolved**, down from 95 before the run —
"Scott (VA)" and "Velazquez" both now show correct party.

**2. Row-count arithmetic checks out exactly.** Total US Congress vote records with a usable
note: 534,522. Before the run: 147,473 unresolved. After: 3,133 unresolved. That's exactly
144,340 resolved — matching the script's own reported count and this doc's total — with no
rows added or removed (534,522 before and after), confirming this was a pure fill-in-the-blanks
update, not an insert/delete that could have changed the shape of the data.

**3. Only the 220 legislators listed above were affected — confirmed, not just assumed.**
Recomputed, from scratch, which person every noted vote *should* resolve to, and compared
against what's actually stored now. The backfill script can only ever write a value it itself
computed via that same identifier lookup for a row that was null beforehand — so by
construction it cannot silently write a wrong or unexpected person. Verified this held in
practice, not just in theory.

**One unrelated, pre-existing issue turned up during this check — not caused by, or part of,
today's backfill.** 62 vote records (all bioguide `G000551`) currently show a person whose ID
disagrees with what a fresh identifier lookup computes. These rows already had a (non-null)
`voter_id` *before* today's run, so the backfill's `voter_id IS NULL` filter always excluded
them — they were never touched. Traced the cause: `G000551` belongs to **Raúl Grijalva**, but
these 62 votes are currently attributed to **Adelita Grijalva** (his successor in the same
seat, sharing his surname) — almost certainly a leftover mis-match from the old name-only
matching this whole OPEN-2 fix replaced, on a case the identifier-based backfill can't reach
because it's not a null row. Confirmed none of these 62 rows are among the 220 legislators/
144,340 votes listed above (Grijalva doesn't appear in this doc's table at all). Flagging as a
separate, pre-existing data-quality item worth its own look — out of scope for this backfill,
since fixing it would mean *overwriting* an existing value, not filling in a blank, which this
script deliberately never does.
