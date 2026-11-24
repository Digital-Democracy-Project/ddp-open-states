# addendum to my question on the plain API keys (task definition): what ddp-sync's own secret holds (names and lengths only)

Ramon asked me to look in Secrets Manager from this host (read only; no value printed or written anywhere).

- Secret `ddp-sync/credentials` (the one ddp-sync's config loads; 38 keys). Its key names are lowercase.
- `congress_api_key`: **present, length 40**. The task definition's `CONGRESS_GOV_API_KEY` is also length 40. I did not compare the two values (that would mean putting a value into a command), so "same key" is unverified; only the shape matches.
- **Virginia: no key in this secret** under va_api_key, virginia_api_key or lis_api_key (and no other name containing "virg", "lis" or "va_"). The task definition's `VA_API_KEY` is length 36.
- So the Congress key plausibly already lives in Secrets Manager (ddp-sync's secret); the Virginia key has no Secrets Manager home that I can see from here. If you move both off the task definition, Virginia's needs a secret first. I did not look in other secrets.
