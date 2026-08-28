#!/usr/bin/env python3
import json, sqlite3
PID = "091e47913906cd1eb38e2e2eae0eb425"
db = sqlite3.connect("/var/lib/pandaspool/app.sqlite3")
db.row_factory = sqlite3.Row
print("===PRODUCT===")
print(dict(db.execute("select id,brand,product_line,material from products where id=?", (PID,)).fetchone()))
print("===INBOX===")
for r in db.execute("select id,name,status,sha256,mime,size,created_at from inbox where product_id=? order by created_at", (PID,)):
    print(json.dumps(dict(r), ensure_ascii=False))
print("===TEMP/DRY CLAIMS===")
for r in db.execute("""
select id,source,status,claim_key,claim_value,unit,raw
from claims where product_id=? and (
  claim_key like '%喷嘴%' or claim_key like '%热床%' or claim_key like '%烘干%' or claim_key like '%打印温度%' or claim_key like '%速度%'
) order by claim_key
""", (PID,)):
    print(json.dumps(dict(r), ensure_ascii=False))
