#!/usr/bin/env python3
import json, sqlite3
db = sqlite3.connect("/var/lib/pandaspool/app.sqlite3")
db.row_factory = sqlite3.Row
print("===CLAIMS===")
for r in db.execute("""
select p.brand, p.product_line, p.material, c.source, c.status, c.claim_key, c.claim_value, c.unit, c.raw
from claims c join products p on p.id=c.product_id
where c.status!='rejected'
order by p.brand, p.product_line, p.material, c.claim_key, c.source
"""):
    print(json.dumps(dict(r), ensure_ascii=False))
