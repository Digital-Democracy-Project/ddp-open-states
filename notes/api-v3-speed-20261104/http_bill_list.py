"""OPEN-484 / OPEN-489: HTTP timing of api-v3's newest-action bill list. Read-only (GET only).
Run from the broker web container (or anywhere that reaches api-v3):
  V3_BASE=http://<api-v3 host:port> V3_KEY=<the broker's own api-v3 key> python3 -I http_bill_list.py "<label>" [runs]
The key comes from the environment and is never printed. 1.5 s between calls. Prints the median/min/max for page 1, page 500 and
jurisdiction=us page 1, a fingerprint of the first 20 bill ids of page 1, and total_items (the fingerprint must be the same in every stage)."""
import hashlib, json, os, statistics, sys, time, urllib.request
label = sys.argv[1]; runs = int(sys.argv[2]) if len(sys.argv) > 2 else 15
base, key = os.environ["V3_BASE"].rstrip("/"), os.environ["V3_KEY"]
CALLS = [("page 1", "/bills?sort=latest_action_desc&per_page=20"), ("page 500", "/bills?sort=latest_action_desc&per_page=20&page=500"), ("US page 1", "/bills?sort=latest_action_desc&per_page=20&jurisdiction=us")]
def get(path):
    t = time.perf_counter(); r = urllib.request.urlopen(urllib.request.Request(base + path, headers={"X-API-KEY": key}), timeout=60); b = r.read(); return (time.perf_counter() - t) * 1000, b
print(f"## {label}")
for name, path in CALLS:
    get(path); ts = []
    for _ in range(runs):
        time.sleep(1.5); ms, b = get(path); ts.append(ms)
    if name == "page 1":
        d = json.loads(b); ids = [x["id"] for x in d["results"]]; total = d["pagination"]["total_items"]
    print(f"  {name:10} median {statistics.median(ts):6.0f} ms   min {min(ts):6.0f}   max {max(ts):6.0f}")
print("  first-20 ids fingerprint:", hashlib.sha256(",".join(ids).encode()).hexdigest()[:12], "| total_items:", total)
