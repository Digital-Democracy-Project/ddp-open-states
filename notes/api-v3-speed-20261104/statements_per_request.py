"""OPEN-484 / OPEN-489. Server-side split, run INSIDE the api container: docker exec -i <api container> python - < statements_per_request.py   (read-only). Calls the real endpoint (key check skipped) and times each SQL statement."""
import re, statistics, time
from sqlalchemy import event
from api.db import engine
from api.main import app
from api.auth import apikey_auth
from fastapi.testclient import TestClient
app.dependency_overrides[apikey_auth] = lambda: "x"
c = TestClient(app); ev = []
event.listen(engine, "before_cursor_execute", lambda cn, cu, st, p, cx, em: ev.append(["s", st, time.perf_counter()]))
event.listen(engine, "after_cursor_execute", lambda cn, cu, st, p, cx, em: ev.append(["e", st, time.perf_counter()]))
path = "/bills?sort=latest_action_desc&per_page=20"; c.get(path)
cnt, page, wall, nst, order_in_count = [], [], [], [], None
for _ in range(7):
    ev.clear(); a = time.perf_counter(); r = c.get(path); wall.append((time.perf_counter() - a) * 1000)
    starts = [e for e in ev if e[0] == "s"]; nst.append(len(starts))
    for s, e in zip([x for x in ev if x[0] == "s"], [x for x in ev if x[0] == "e"]):
        ms = (e[2] - s[2]) * 1000
        if " ".join(s[1].split()).startswith("SELECT count(*)"): cnt.append(ms); order_in_count = "ORDER BY" in s[1]
        else: page.append(ms)
print(f"  whole request {statistics.median(wall):6.0f} ms | count statement {statistics.median(cnt):6.0f} ms (ORDER BY inside: {order_in_count}) | page statement {statistics.median(page):6.0f} ms | statements per request: {statistics.median(nst):.0f}")
