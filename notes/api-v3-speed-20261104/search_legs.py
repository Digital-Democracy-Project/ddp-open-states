"""OPEN-485 legs. Run INSIDE the api-v3 container:  docker exec -i <api container> python - < search_legs.py
Read-only SELECTs (EXPLAIN ANALYZE of the full-text leg executes the SELECT only). Prints no credentials."""
import re, statistics, time
from sqlalchemy import text
from api.db import SessionLocal
from api import ddp_search as s

db = SessionLocal()
jids = [r[0] for r in db.execute(text("select distinct jurisdiction_id from ddp_bill_search")).fetchall()]
print("ddp_bill_search rows:", db.execute(text("select count(*) from ddp_bill_search")).scalar(), " jurisdictions:", len(jids))
print("sizes (heap, total, indexes):", db.execute(text("select pg_size_pretty(pg_relation_size('ddp_bill_search')), pg_size_pretty(pg_total_relation_size('ddp_bill_search')), pg_size_pretty(pg_indexes_size('ddp_bill_search'))")).fetchall())
def timed(label, stmt, p, n=5):
    xs = []
    for _ in range(n):
        s._use_similarity_threshold(db)
        a = time.perf_counter(); r = db.execute(stmt, p).fetchall(); xs.append((time.perf_counter() - a) * 1000)
    print(f"  {label:34} first {xs[0]:7.0f}  median {statistics.median(xs):7.0f} ms  rows={len(r)}")
for q in ["health care", "tax", "pelosi"]:
    like = s._like(q)
    p = {"q": q, "jids": jids, "limit": 100, "session": None, "like": like}
    print(f"== {q!r} (phrase={bool(like)})")
    timed("full-text leg", s.FTS_PHRASE_SQL if like else s.FTS_SQL, p)
    timed("fuzzy-title leg", s._fuzzy_title(p), p)
    a = time.perf_counter(); s._people_hits(db, p); print(f"  {'people leg':34} one run {(time.perf_counter() - a) * 1000:7.0f} ms")
    print("  candidates matching the full-text query:", db.execute(text("select count(*) from ddp_bill_search x, websearch_to_tsquery('english', :q) qq where x.fts @@ qq"), p).scalar())
p = {"q": "health care", "jids": jids, "limit": 100, "session": None, "like": s._like("health care")}
for run in (1, 2):
    print(f"\n--- EXPLAIN (ANALYZE, BUFFERS) of the 'health care' full-text leg, run {run}")
    for r in db.execute(text("EXPLAIN (ANALYZE, BUFFERS) " + str(s.FTS_PHRASE_SQL)), p).fetchall():
        l = r[0]
        if re.search(r"Sort Key|Sort Method|Heap Scan|Index Scan|Execution Time|Planning Time|Buffers: shared", l):
            print("   ", l.strip()[:150])
print("\n--- facts")
one = lambda x: db.execute(text(x)).fetchall()
for k in ("shared_buffers", "work_mem", "random_page_cost", "effective_cache_size", "max_parallel_workers_per_gather"):
    print(f"{k}:", one(f"show {k}")[0][0])
print("cache hit counters (this database):", one("select blks_hit, blks_read from pg_stat_database where datname = current_database()"))
