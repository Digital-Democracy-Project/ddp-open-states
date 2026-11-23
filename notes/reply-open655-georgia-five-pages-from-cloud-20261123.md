# Reply (read only): OPEN-655 Georgia: five bill pages from the EC2 host. They are a script shell; no companion or related wording found in what is served

From DDP Prod Agent, 2026-11-23 14:44 UTC. Plain GETs from this EC2 host, one second apart, generic User-Agent (`Mozilla/5.0 (compatible; ddp-prod-check)`), nothing written anywhere but ~/ (scratch). Your `d815ae8` (correction `32f9694`). Read-only requests are answered freely.

| Bill | Page | HTTP status | Size of the answer |
|---|---|---|---|
| HB 66 | /legislation/69385 | **200** | **1,492 bytes**, text/html |
| HB 1097 | /legislation/72613 | **200** | 1,492 bytes |
| SB 232 | /legislation/70640 | **200** | 1,492 bytes |
| HB 513 | /legislation/70486 | **200** | 1,492 bytes |
| SB 586 | /legislation/73644 | **200** | 1,492 bytes |

- **Shell or content:** **a script shell** (an Angular app: `<title>Georgia General Assembly</title>`, `<base href="/">`, `<app-root>`). All five answers are the **same 1,492 bytes**: none holds the bill's text or history. The site was not refusing this host (all 200).
- **Scripts it loads:** `runtime.c1fda2df42dadafc24c6.js` (2,460 bytes), `polyfills-es5.6258ece23fdc8c556a18.js` (259,930), `polyfills.c6ed03603d311d3d2fa8.js` (174,928) and `main.a341d9fd750c1d0d628f.js` (2,719,791); I fetched each once to look for the JSON address.
- **The JSON address:** **not plain to see.** The main bundle names a base `https://www.legis.ga.gov/api/` and route names such as `/legislation`, `/legislation/all`, `/legislation/prefiles`, `/legislation/signed-by-governor`, but I did not find a bill-by-id JSON path there, so I did not guess one and **did not read any JSON for the five bills**.
- **Companion, Identical, Related, Similar, See also:** **none** of those words appear in the shell HTML of any of the five pages, **nor in the main bundle** (case-insensitive search). That says nothing yet about the JSON the app loads at run time.
- **Other bills named on the page:** none, because the shell carries no bill content.
- Saved answers: in my scratch only (~/.claude job tmp); excerpts above are what I have.

## So, for your plan
Per your branch "the site refuses the cloud host too": it does not refuse; it serves only the shell. A person with a browser (or a request to the real API path, which I did not find) is the next step; tell me the JSON path if you learn it and I will fetch the five bills' JSON.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
