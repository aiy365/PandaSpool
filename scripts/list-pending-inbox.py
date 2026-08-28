#!/usr/bin/env python3
import json, sqlite3, os
db = sqlite3.connect("/var/lib/printpilot/app.sqlite3")
db.row_factory = sqlite3.Row
print("===PENDING===")
for r in db.execute("""
select i.id, i.product_id, p.brand, p.product_line, p.material, i.name, i.mime, i.size, i.status, i.created_at, i.sha256
from inbox i join products p on p.id=i.product_id
where i.status='pending'
order by i.created_at, i.name
"""):
    print(json.dumps(dict(r), ensure_ascii=False))
print("===PENDING COUNT===", db.execute("select count(*) from inbox where status='pending'").fetchone()[0])
print("===FILES DIR===")
print("/var/lib/printpilot/files/inbox")
os.system("ls -l /var/lib/printpilot/files/inbox | tail -n 30")
