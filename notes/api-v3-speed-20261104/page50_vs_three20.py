"""OPEN-493: one page of 50 bills, three simultaneous calls of 20 (today) against one call of 50. Read-only (GET only).
Run from the broker web container (or anywhere that reaches api-v3):
  V3_BASE=http://<api-v3 host:port> V3_KEY=<the broker's own api-v3 key> python3 -I page50_vs_three20.py "<label>" [runs]
The key comes from the environment and is never printed. 1.5 s between runs. Before the api-v3 change, per_page=50 is a 400: that is reported, not an error."""
import hashlib, json, os, statistics, sys, time, urllib.error, urllib.request, concurrent.futures as cf
label = sys.argv[1]; runs = int(sys.argv[2]) if len(sys.argv) > 2 else 15
base, key = os.environ["V3_BASE"].rstrip("/"), os.environ["V3_KEY"]
BASE = "/bills?sort=latest_action_desc"
def get(path):
    t = time.perf_counter()
    try:
        r = urllib.request.urlopen(urllib.request.Request(base + path, headers={"X-API-KEY": key}), timeout=60); body = json.loads(r.read()); code = r.status
    except urllib.error.HTTPError as e:
        body, code = {}, e.code
    return (time.perf_counter() - t) * 1000, code, body
def three():
    t = time.perf_counter()
    with cf.ThreadPoolExecutor(3) as ex: res = list(ex.map(lambda p: get(f"{BASE}&per_page=20&page={p}"), (1, 2, 3)))
    return (time.perf_counter() - t) * 1000, [x["id"] for _, _, d in res for x in d.get("results", [])][:50], [c for _, c, _ in res]
print(f"## {label}")
three(); ts = []
for _ in range(runs):
    time.sleep(1.5); ms, ids3, codes = three(); ts.append(ms)
print(f"  3 x per_page=20 at once   median {statistics.median(ts):6.0f} ms   min {min(ts):6.0f}   max {max(ts):6.0f}   (status {sorted(set(codes))})")
fp3 = hashlib.sha256(",".join(ids3).encode()).hexdigest()[:12]
ms, code, d = get(f"{BASE}&per_page=50")
if code != 200:
    print(f"  1 x per_page=50           HTTP {code} (expected before the change)"); print("  first-50 ids fingerprint (three calls):", fp3)
else:
    ts = []
    for _ in range(runs):
        time.sleep(1.5); ms, code, d = get(f"{BASE}&per_page=50"); ts.append(ms)
    ids50 = [x["id"] for x in d["results"]]
    print(f"  1 x per_page=50           median {statistics.median(ts):6.0f} ms   min {min(ts):6.0f}   max {max(ts):6.0f}   (status {code})")
    print("  first-50 ids fingerprint: three calls", fp3, "| one call", hashlib.sha256(",".join(ids50).encode()).hexdigest()[:12], "| rows:", len(ids50), "| total_items:", d["pagination"]["total_items"], "| max_page:", d["pagination"]["max_page"])
    for n, extra in ((51, ""), (50, "&include=sponsorships")):
        _, c, _ = get(f"{BASE}&per_page={n}{extra}"); print(f"  per_page={n}{' with include=' if extra else ''}: HTTP {c} (expected 400)")
