#!/usr/bin/env python3
import json, sqlite3
db = sqlite3.connect("/var/lib/pandaspool/app.sqlite3")
db.row_factory = sqlite3.Row
print("===SHELF===")
for r in db.execute("""
select p.brand, p.product_line, p.material, c.name, c.color_family, c.unopened, c.opened, c.notes
from colors c join products p on p.id=c.product_id
where c.unopened>0 or c.opened>0
order by p.brand, p.product_line, p.material, c.name
"""):
    print(json.dumps(dict(r), ensure_ascii=False))
print("===FAMILY===")
for r in db.execute("""
select ifnull(nullif(c.color_family,''),'未分类') fam,
       sum(c.unopened) u, sum(case when c.opened>0 then 1 else 0 end) o,
       sum(c.unopened + case when c.opened>0 then 1 else 0 end) spools
from colors c
where c.unopened>0 or c.opened>0
group by fam order by spools desc
"""):
    print(json.dumps(dict(r), ensure_ascii=False))
