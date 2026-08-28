import json, sqlite3
db = sqlite3.connect("/var/lib/printpilot/app.sqlite3")
db.row_factory = sqlite3.Row
print("===PRODUCTS===")
for r in db.execute("select id,brand,product_line,material,notes from products order by brand, product_line, material"):
    print(json.dumps(dict(r), ensure_ascii=False))
print("===COLORS===")
for r in db.execute("""
select p.brand, p.product_line, p.material, c.id, c.product_id, c.name, c.color_family, c.unopened, c.opened, c.notes
from colors c join products p on p.id=c.product_id
order by p.brand, p.product_line, p.material, c.name
"""):
    print(json.dumps(dict(r), ensure_ascii=False))
