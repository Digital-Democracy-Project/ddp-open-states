# WARNING: ddp-sync's Secrets Manager secret is not valid JSON after Ramon's edit; my step 3 restart is cancelled until it parses

Ramon added `va_api_key` to the secret `ddp-sync/credentials` (11-24 ~22:40 UTC) and asked me to recheck. No value printed or stored anywhere.

- Recheck: `json.loads` of the secret string fails: **"Expecting ',' delimiter: line 15 column 3 (char 974)"**. A comma is most likely missing at the end of line 14 (before the new entry) or the new line has a stray quote. I could not read the new key because the secret does not parse.
- **Action taken:** I stopped my guarded ddp-sync restart job (AZ canary step 3, `up -d --no-deps`), because a restart would load this secret. Verified: no restart job process is left; the container still runs from 20:15:51 UTC; 0 Tracebacks and no Secrets Manager error lines in the last 20 minutes (it read the secret at startup).
- **Please:** nobody should restart or rebuild ddp-sync, and no other reader of that secret should be re-triggered, until Ramon has fixed it and I confirm it parses. I will recheck on his word and report, then re-stage the step 3 restart (still the config-only change, #311 already pulled: /opt/ddp-sync is at 6d56c64).
- Earlier finding stands for the rest: the secret had `congress_api_key` (length 40) and no Virginia key before this edit; the task definition's `VA_API_KEY` is length 36.
