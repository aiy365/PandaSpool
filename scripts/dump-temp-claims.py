#!/usr/bin/env python3
import json, sqlite3
db = sqlite3.connect("/var/lib/printpilot/app.sqlite3")
db.row_factory = sqlite3.Row
for r in db.execute("""
select p.brand, p.product_line, p.material, c.id, c.source, c.status, c.claim_key, c.claim_value, c.unit, ifnull(c.color_id,'') color_id, c.raw
from claims c join products p on p.id=c.product_id
where c.status!='rejected' and (
  c.claim_key like '%喷嘴%' or c.claim_key like '%打印温度%' or c.claim_key like '%热床%' or c.claim_key like '%预设打印%'
)
order by p.brand, p.material, c.claim_key
"""):
    print(json.dumps(dict(r), ensure_ascii=False))
