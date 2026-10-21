#!/usr/bin/env python3
"""
Nightly contract check for the published sites.

Watches the machine-readable contracts other people's code depends on (sitemaps,
canonical URLs, JSON APIs) and writes a timestamped snapshot so a regression is
visible the morning after it happens, not the month after.

Deliberately does NOT store page bodies or personal data — only counts, status
codes, and content hashes.
"""
import hashlib, json, os, re, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "snapshots")
UA = "contract-check/1.0 (+https://github.com/parbarshop)"

TARGETS = [
    {"site": "orbisica", "sitemap": "https://orbisica.com/sitemap.xml"},
    {"site": "kitchenmind", "sitemap": "https://kitchenmindai.com/sitemap.xml"},
    {"site": "utiqo", "sitemap": "https://utiqo.com/sitemap.xml"},
    {"site": "tintiva", "sitemap": "https://tintiva.com/sitemap.xml"},
    {"site": "emojiselect", "sitemap": "https://emojiselect.com/sitemap.xml"},
]

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()

def locs(xml):
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml.decode("utf-8", "replace"))

def check(t):
    rec = {"site": t["site"], "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        code, body = fetch(t["sitemap"])
        rec["sitemap_status"] = code
        rec["sitemap_bytes"] = len(body)
        rec["sitemap_sha256_12"] = hashlib.sha256(body).hexdigest()[:12]
        urls = locs(body)
        rec["child_sitemaps"] = len([u for u in urls if u.endswith(".xml")])
        rec["url_count"] = len([u for u in urls if not u.endswith(".xml")])
        rec["sample_urls"] = urls[:3]
        rec["ok"] = code == 200 and len(urls) > 0
    except urllib.error.HTTPError as e:
        rec["sitemap_status"] = e.code
        rec["ok"] = False
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"
        rec["ok"] = False
    return rec

def main():
    os.makedirs(OUT, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    results = [check(t) for t in TARGETS]
    snap = {"run": stamp, "results": results}
    json.dump(snap, open(os.path.join(OUT, f"{stamp}.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    # latest.json is the pointer; diffing is done against the previous file
    latest = os.path.join(OUT, "latest.json")
    prev = json.load(open(latest, encoding="utf-8")) if os.path.exists(latest) else None
    json.dump(snap, open(latest, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    changes = []
    if prev:
        pm = {r["site"]: r for r in prev["results"]}
        for r in results:
            p = pm.get(r["site"], {})
            if p.get("url_count") != r.get("url_count"):
                changes.append(f"{r['site']}: url_count {p.get('url_count')} -> {r.get('url_count')}")
            if p.get("sitemap_status") != r.get("sitemap_status"):
                changes.append(f"{r['site']}: status {p.get('sitemap_status')} -> {r.get('sitemap_status')}")

    for r in results:
        n = r.get("url_count", "-")
        extra = " [SITEMAP INDEX]" if r.get("child_sitemaps") else ""
        print(f"{r['site']:13s} status={r.get('sitemap_status')} urls={n}{extra} ok={r.get('ok')}")
    print()
    if changes:
        print("CHANGES SINCE LAST RUN:")
        for c in changes:
            print("  !", c)
    else:
        print("No contract changes since last run." if prev else "Baseline established (no previous run).")
    return 1 if any(not r.get("ok") for r in results) else 0

if __name__ == "__main__":
    sys.exit(main())
