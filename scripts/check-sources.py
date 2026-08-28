#!/usr/bin/env python3
import sqlite3
db = sqlite3.connect("/var/lib/pandaspool/app.sqlite3")
print("sources", list(db.execute("select source, count(*) from claims group by source")))
print("pending", db.execute("select count(*) from inbox where status='pending'").fetchone()[0])
print("drafts", db.execute("select count(*) from claims where status='draft'").fetchone()[0])
bad = list(db.execute("select distinct source from claims where source in ('厂家','商家')"))
print("old_sources_left", bad)
print("new_product_drafts")
ids = (
    "e67ce04e60e9c691325962ff0599a5f5",
    "dccccccf8f4c5dfc32cb0770db448d00",
    "4e13903217d281cbc482ee5182c40276",
    "26fbf5e0f6e3b14d236b8d35dabace62",
)
q = ",".join("?" * len(ids))
for r in db.execute(
    "select p.brand, p.product_line, p.material, c.source, c.claim_key, c.claim_value, c.unit "
    "from claims c join products p on p.id=c.product_id "
    f"where c.status='draft' and c.product_id in ({q}) "
    "order by p.brand, p.material, c.claim_key",
    ids,
):
    print(" | ".join("" if x is None else str(x) for x in r))
