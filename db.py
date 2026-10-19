import json, sqlite3
from datetime import datetime
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "inspections.db"


def _c():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _c() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS inspections(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, day TEXT, name TEXT, part_type TEXT,
            defects TEXT, decision TEXT, action TEXT, image TEXT, verified INTEGER DEFAULT 0)""")


def add(name, part_type, defects, decision, action, image):
    now = datetime.now()
    with _c() as c:
        cur = c.execute("INSERT INTO inspections(ts,day,name,part_type,defects,decision,action,image) VALUES(?,?,?,?,?,?,?,?)",
                        (now.strftime("%H:%M:%S"), now.strftime("%Y-%m-%d"), name, part_type,
                         json.dumps(defects), decision, action, image))
        return cur.lastrowid


def rows(day):
    with _c() as c:
        out = [dict(r) for r in c.execute("SELECT * FROM inspections WHERE day=? ORDER BY id DESC", (day,))]
    for r in out:
        r["defects"] = json.loads(r["defects"])
    return out


def verify(i):
    with _c() as c:
        c.execute("UPDATE inspections SET verified=1 WHERE id=?", (i,))


def stats(day):
    r = rows(day)
    s = {"day": day, "checked": len(r), "verified": sum(x["verified"] for x in r),
         "PASS": 0, "REWORK": 0, "RECYCLE": 0, "defect_types": {}}
    for x in r:
        s[x["decision"]] += 1
        for d in x["defects"]:
            s["defect_types"][d["type"]] = s["defect_types"].get(d["type"], 0) + 1
    s["pass_rate"] = round(100 * s["PASS"] / s["checked"], 1) if s["checked"] else 0
    return s
