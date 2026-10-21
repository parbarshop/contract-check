# contract-check

A small nightly regression check for sites whose sitemaps and canonical URLs other
people's code depends on. It answers one question every morning: **did anything I
publish break overnight?**

## Why this exists

Sitemaps rot quietly. A deploy changes a route, a locale prefix gets reordered, a
page type is regenerated with a different canonical — and nothing errors. The site
serves 200s, the sitemap serves 200, and the only symptom is a slow loss of
indexed URLs that shows up weeks later in search console charts.

Point-in-time audits miss this because they capture one moment. A nightly snapshot
of counts, status codes and content hashes makes the *change* visible instead.

## What it checks

For each configured site:

| field | meaning |
|---|---|
| `sitemap_status` | HTTP status of the sitemap or sitemap index |
| `url_count` | number of `<loc>` entries (excluding child sitemaps) |
| `child_sitemaps` | count of nested `.xml` children (per-locale sitemap indexes) |
| `sitemap_bytes` | response size — a sudden shrink means truncated output |
| `sitemap_sha256_12` | first 12 hex chars of the body hash |
| `sample_urls` | first three URLs, for a quick eyeball on shape |

It deliberately stores **no page bodies and no visitor data** — only counts,
codes and hashes. Nothing here identifies a user.

## Usage

```bash
python scripts/contract_check.py
```

Exit code is `0` when every sitemap resolved with at least one URL, `1` otherwise,
so it drops straight into cron or CI. Every run writes
`snapshots/<UTC timestamp>.json` and updates `snapshots/latest.json`; when a
previous snapshot exists the run prints a diff:

```
CHANGES SINCE LAST RUN:
  ! orbisica: url_count 718 -> 701
  ! utiqo: status 200 -> 503
```

## Design notes

- **Sitemap index handling.** Sites that publish per-locale sitemaps return a
  sitemap index rather than a flat urlset, so `url_count` is `0` for them and
  `child_sitemaps` carries the signal. Treating that as a failure would produce a
  false alarm every night, so the ok-check only requires a 200 with at least one
  `<loc>` of either kind.
- **Hashes over diffs.** Storing a short hash lets you detect "the sitemap changed"
  without keeping a copy of every published URL on every run.
- **No writes to the target.** This is a read-only observer. It never touches a
  server it monitors.

## Adding a site

Append an entry to `TARGETS` in `scripts/contract_check.py`:

```python
{"site": "example", "sitemap": "https://example.com/sitemap.xml"}
```

## Licence

MIT.
