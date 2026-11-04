"""OPEN-484 baseline. Run INSIDE the api-v3 container:  docker exec -i <api container> python - < bills_explain.py
Read-only: builds the endpoint's own page and count queries, runs EXPLAIN (ANALYZE, BUFFERS) on them (EXPLAIN ANALYZE
executes the SELECT only), and reads settings and ownership. Creates and changes nothing. Prints no credentials."""
import re, statistics, time
from sqlalchemy import desc, func, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.expression import nullslast
from api.db import SessionLocal, models
from api import bills as b

db = SessionLocal()
q = b.base_query(db).order_by(nullslast(desc(models.Bill.latest_action_date)), models.Bill.id)
def sql(x):
    return str(x.statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
page = lambda off: sql(q.limit(20).offset(off))
count = sql(db.query(func.count()).select_from(q.order_by(None).subquery()))
total = db.execute(text("select count(*) from opencivicdata_bill")).scalar()
print("bills:", total)

def plan(label, stmt, n=3):
    times = []
    for i in range(n):
        rows = [r[0] for r in db.execute(text("EXPLAIN (ANALYZE, BUFFERS) " + stmt)).fetchall()]
        ex = next(float(re.search(r"Execution Time: ([\d.]+)", r).group(1)) for r in rows if "Execution Time" in r)
        times.append(ex)
        if i == 0:
            print(f"\n--- {label}: plan of run 1 (node types and buffers only)")
            for r in rows:
                if re.search(r"Scan|Sort|Join|Limit|Gather|Aggregate|Buffers: shared|Execution Time|Planning Time|Workers", r):
                    print("   ", r.strip()[:150])
    print(f"{label}: Execution Time ms, {n} runs: {times}  median {statistics.median(times):.1f}")

plan("PAGE 1 (offset 0)", page(0))
plan("PAGE MIDDLE (offset %d)" % (total // 2), page(total // 2))
plan("COUNT (the page's total)", count)
t = []
for _ in range(5):
    a = time.perf_counter(); db.execute(text(page(0))).fetchall(); t.append((time.perf_counter() - a) * 1000)
print("page 1 wall ms from this process (5 runs):", [round(x) for x in t])

print("\n--- facts")
one = lambda s: db.execute(text(s)).fetchall()
print("owner of opencivicdata_bill / current_user:", one("select pg_get_userbyid(relowner), current_user from pg_class where relname='opencivicdata_bill'"))
print("indexes on opencivicdata_bill:", [r[0] for r in one("select indexname from pg_indexes where tablename='opencivicdata_bill'")])
print("sizes (heap, total):", one("select pg_size_pretty(pg_relation_size('opencivicdata_bill')), pg_size_pretty(pg_total_relation_size('opencivicdata_bill'))"))
for s in ("shared_buffers", "max_parallel_workers_per_gather", "work_mem", "random_page_cost", "effective_cache_size", "server_version"):
    print(f"{s}:", one(f"show {s}")[0][0])
print("cache hit counters (this database):", one("select blks_hit, blks_read from pg_stat_database where datname = current_database()"))
