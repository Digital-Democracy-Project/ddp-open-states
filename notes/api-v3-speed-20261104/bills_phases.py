"""OPEN-484 phase timing. Run INSIDE the api-v3 container:  docker exec -i <api container> python - < bills_phases.py
Read-only. Repeats what GET /bills?sort=latest_action_desc&per_page=20 does, step by step, and times each step, so the
time that is neither the page query nor the count shows up. Skips the key check on purpose (it is not what is measured).
Prints no credentials."""
import statistics, time
from sqlalchemy import desc
from sqlalchemy.sql.expression import nullslast
from api.db import SessionLocal, models
from api import bills as b

def run():
    db = SessionLocal(); t = {}
    a = time.perf_counter()
    q = b.base_query(db).order_by(nullslast(desc(models.Bill.latest_action_date)), models.Bill.id)
    t["build query"] = time.perf_counter() - a
    a = time.perf_counter(); total = q.count(); t["count (round trip)"] = time.perf_counter() - a
    pg = b.BillPagination(page=1, per_page=20)
    a = time.perf_counter(); r2 = pg.select_or_noload(q, []); t["options"] = time.perf_counter() - a
    a = time.perf_counter(); rows = r2.limit(20).offset(0).all(); t["page query + load rows"] = time.perf_counter() - a
    a = time.perf_counter(); objs = [pg.to_obj_with_includes(x, [], detail=False) for x in rows]; t["rows to response objects"] = time.perf_counter() - a
    a = time.perf_counter(); b.BillPagination.response_model()(results=objs, pagination={"per_page": 20, "page": 1, "max_page": 1, "total_items": total}).json(); t["encode as JSON"] = time.perf_counter() - a
    db.close(); return {k: v * 1000 for k, v in t.items()}
run()
res = [run() for _ in range(7)]
tot = [sum(r.values()) for r in res]
for k in res[0]:
    print(f"{k:28} median {statistics.median(r[k] for r in res):7.1f} ms   max {max(r[k] for r in res):7.1f}")
print(f"{'TOTAL of these steps':28} median {statistics.median(tot):7.1f} ms   max {max(tot):7.1f}")
