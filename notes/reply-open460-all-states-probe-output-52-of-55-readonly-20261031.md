# Reply: OPEN-460 all-states probe output (read-only), 2026-10-31 ~18:55 UTC. 52 of 55 committed; DE still running; CA and VT crashed

**Heads up: I read before your "final exit codes" update** (the user asked me to go ahead, and I saw no update note). So this is a partial read; anything still running is called out. I changed nothing and did not print the task token (the botocore tails are omitted).

## Counts
- Prefix `dev-probe-all-20261031/`: **155 objects, 926,701 bytes** (at 18:51 UTC). 52 states have `result.json`.
- **Written outside the prefix since 18:30 UTC: nothing** (`working-tier/`, `prod/`, `access-tests/`, the three earlier `dev-probe-co-*` prefixes: 0 new objects).
- Committed unchanged: `notes/probe-all-20261031/<st>/result.json` and `report.md` for **ak al ar az co ct dc fl ga gu hi ia id il in ks ky la ma md me mn mo mp ms mt nc nd ne nh nj nm nv ny oh ok or pa pr ri sc sd tn tx us ut va vi wa wi wv wy** (no `sample.tar.gz`). Secret scan of everything committed: clean.
- Classification: **38 YELLOW, 14 RED, 0 GREEN.**

## Not committed
- **de (Delaware): still running at 18:51 UTC** (log was still moving through legis.delaware.gov at 18:49; no `result.json` yet). I will read it when it ends if you ask.
- **ca (California) and vt (Vermont): the task crashed before writing any report.** See `digest-crashed-no-report.md`. CA: `ModuleNotFoundError: No module named 'MySQLdb'` (the CA bill scraper builds a MySQL connection in `__init__`; the image has no mysqlclient). VT: `TypeError: object of type 'generator' has no len()` at `verify-jurisdiction` line 421 in gate A (`len(scraped_sessions)` on a generator, i.e. a probe-tool bug, not VT's site).

## The 14 RED states and the blocking failure (details in `digest-red-states.md`)
| state | blocking failure |
|---|---|
| ar | D: dry scrape wrote zero objects (`ARBillScraper raised EmptyScrape`; the FTPDocument fetches return 2 bytes) |
| ct | D: `FTPError` retrieving ftp://ftp.cga.ct.gov/pub/data/committee.csv (retries ran past 1 minute) |
| dc | A: `KeyError: 'DC_API_KEY'` (needs a credential in the task environment) |
| il | A: 403 Forbidden from ilga.gov `GetGeneralAssemblies`; D: `KeyError: None` |
| in | A and D: `KeyError('INDIANA_API_KEY')` |
| mn | D: `ScrapeError: no objects returned from MNBillScraper scrape` |
| nh | D: `ConnectionError ... Remote end closed connection without response` |
| nj | D: `ScrapeError: no objects returned from NJBillScraper scrape` |
| nm | D: `FileNotFoundError: 'mdb-export'` (mdbtools is not in the image) |
| ny | A and D: `KeyError('NEW_YORK_API_KEY')` |
| tn | D: `IndexError: list index out of range` |
| tx | D: `TimeoutError: [Errno 110] Connection timed out` |
| vi | A and D: `ConnectTimeout` to billtracking.legvi.org:8082 (it retried for several minutes and then uploaded) |
| wi | D: `HTTPError: 429` from docs.legis.wisconsin.gov |

Credential-related (dc, in, ny) and missing-tool cases (nm `mdb-export`, ca `MySQLdb`) are environment gaps in the task, not site blocks; il (403), wi (429) and tx/nh/ct/vi (network) look like site or network behavior. I have not verified any of these beyond what the logs and reports say.

Task ids per state are in the digests (RED, crashed) and in `listing` order of the log group; the other 38 YELLOW states uploaded all three files with no traceback in the stream tail that I read.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
