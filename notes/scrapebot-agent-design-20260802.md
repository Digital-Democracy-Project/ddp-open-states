# Sketch: ScrapeBot — a general-purpose CAMS agent for cookie-minting via a headed browser

**Status: proposal, not built.** Written at the operator's request to generalize
`notes/mi-cams-headed-browser-spec-20260802.md`'s "Option A" (cookie-minting only, not routing
all traffic through the browser) into a real CAMS agent that isn't hardcoded to Michigan — any
jurisdiction that starts tripping bot detection should be a config change, not a new code path.
This is a design sketch for review, not an implementation.

## Why a new agent, not a feature bolted onto an existing one

This is browser automation, not reasoning or drafting — closer to LegBot's shape (one task_type,
a short deterministic pipeline) than GrantBot's (multi-step orchestration with an LLM driving
navigation). No model routing, no `ModelRouter`, no Claude/Ollama call in the hot path at all.
Keeping it a separate agent also keeps its own persistent browser profile fully isolated from
GrantBot's — the MI spec already flagged that GrantBot's OAuth-session profile must never be
shared with a scrape-cookie session.

## Agent shape

- **Agent name:** `scrapebot`
- **One task_type:** `mint_scrape_cookies`
- **Payload:** `{"jurisdiction": "mi"}` — everything else (target URL, which cookies to extract,
  pacing, browser fingerprint) is resolved from config, not supplied by the caller. A caller
  should not be able to point this at an arbitrary URL or override pacing per-call; that keeps
  the whole surface auditable per jurisdiction.

## New config file: `config/scrapebot_jurisdictions.yaml`

```yaml
mi:
  target_url: "https://legislature.mi.gov/"
  cookie_names: ["x-bni-fpc", "x-bni-rncf"]
  profile_dir: "~/.config/scrapebot/browser-profile/mi"
  viewport: {width: 1280, height: 800}
  timezone: "America/Detroit"
  locale: "en-US"
  min_delay_s: 6
  jitter_s: 2
```

A new jurisdiction is a new top-level key here, never a code change — matching this repo's own
stated convention for LegBot's question registry (`config/legbot_questions.yaml`) in the sibling
`ddp-agents` repo: new capability = new config entry, not a new code path.

## Pipeline (3 states, no LLM step)

1. **`RESOLVE_JURISDICTION`** — load the requested jurisdiction's config block. Fail fast with a
   clear, named error if the key doesn't exist — never silently fall back to another
   jurisdiction's settings (e.g. MI's pacing/viewport should never leak into a VA run just because
   VA wasn't configured yet).
2. **`MINT_COOKIES`** — launch or reuse a **persistent Chromium context scoped to that
   jurisdiction** (its own `profile_dir` — never shared with GrantBot's profile, and never shared
   *across* jurisdictions either, so one jurisdiction's block can't contaminate another's
   fingerprint history). Navigate to `target_url` respecting `min_delay_s`/`jitter_s`. Read back
   the configured cookie names **and** that same context's real `navigator.userAgent`.
3. **`COMPLETED`** — write `{"cookies": [...], "user_agent": "...", "captured_at": ...}` to
   working memory via this bot's own `wm_snapshot_keys.py` allowlist entry. Don't skip this step —
   it's exactly the gap that silently broke LegBot's `task_result.json` for weeks after Phase 2
   shipped (see `ddp-agents`'s CLAUDE.md, "Task result snapshot bug found + fixed 2026-07-21").

## The one invariant that generalizes today's actual bug (OPEN-23)

Cookies and the user-agent that minted them are always returned and consumed **as a single atomic
pair**. Nothing downstream may attach these cookies to a request under any other UA string. This
is what today's live MI investigation found broken — three different, unrelated User-Agent
strings sharing one cookie session across `cookie_provider.py`, `mi/bills.py`, and
`base.py`'s `get_random_user_agent()`. A general-purpose ScrapeBot should make that mismatch
structurally impossible to reintroduce, rather than relying on every jurisdiction's scraper code
to remember it independently.

## Pacing default, and why

`min_delay_s: 6` / `jitter_s: 2` isn't arbitrary — it's informed by today's two real data points
(`notes/mi-cams-headed-browser-spec-20260802.md` and its follow-up in this branch's prior PR):
a rapid burst got blocked, while 5 pages spaced ~6-7s apart all came back clean. That's one
positive result for one jurisdiction, not a proven-safe constant — treat it as this agent's
starting default, worth re-validating per jurisdiction as more real traffic runs through it, not
as a settled number.

## Consumer side (`ddp-sync` / `openstates-core`)

Dispatch via the same `POST /api/v1/tasks` path every CAMS bot already uses
(`{"bot": "scrapebot", "task_type": "mint_scrape_cookies", "payload": {"jurisdiction": "mi"}}`),
then read the result out of `task_result.json` on the shared filesystem — no new CAMS HTTP
endpoint needed, reusing the exact pattern `ddp-sync`'s `legbot_client.py` already established for
LegBot. The scraper then attaches the returned cookies to its own `scrapelib`/`requests` client,
using the returned `user_agent` for the lifetime of that cookie pair — this is Option A: the
browser only mints identity, it never becomes the actual data-fetching path (that's Option B,
out of scope here).

## Explicit open questions before building

1. Where does `scrapebot`'s CAMS-side code actually live — a new module under `ddp-agents`
   alongside LegBot/GrantBot (matches every other bot's home), or somewhere in this repo? This
   sketch assumes `ddp-agents`, matching every other CAMS bot's location.
2. Does one shared `scrapebot` LaunchDaemon serve all jurisdictions, or does each jurisdiction's
   persistent profile need its own daemon/process for isolation? This sketch assumes one shared
   daemon, multiple profile directories — worth confirming that's enough isolation.
3. Resource budget: GrantBot's browser workers are already budgeted at 2048MB
   (`ddp-agents`'s `config/workers.mac.yaml`). Does ScrapeBot need its own separate budget line,
   or can it share GrantBot's browser worker pool? This sketch assumes a separate budget, since
   sharing risks exactly the kind of aggregate-footprint problem `mi_cookies.py`'s own docstring
   already warns about.
4. Rollout gate: a `SCRAPEBOT_ENABLED` master flag, matching every other bot's convention
   (`LEGBOT_ENABLED`, `GRANTBOT_*_ENABLED`), is assumed but not yet named definitively.

## References

- `notes/mi-cams-headed-browser-spec-20260802.md` — the MI-specific spec this generalizes
- This branch's prior PR (paced-navigation follow-up) — the pacing evidence behind
  `min_delay_s`/`jitter_s`'s defaults above
- Jira: OPEN-19, OPEN-21, OPEN-22, OPEN-23
- `ddp-agents`'s CLAUDE.md — LegBot section (question-registry convention, `wm_snapshot_keys.py`
  gap precedent), GrantBot section (`config/workers.mac.yaml` browser worker budget)
