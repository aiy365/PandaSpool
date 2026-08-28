
import sqlite3, uuid, datetime

conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()

purchases = [
    # For Polymaker PETG, target line="通用", mat="PETG"
    {"brand": "Polymaker", "line": "通用", "mat": "PETG", "color": "橙色", "price": 30.00, "qty": 1},
    {"brand": "Polymaker", "line": "通用", "mat": "PETG", "color": "深绿色", "price": 30.00, "qty": 1},
    {"brand": "Polymaker", "line": "通用", "mat": "PETG", "color": "黑色", "price": 30.00, "qty": 1},
    
    # For 彩多屋 Silk, target line="Silk", mat="PLA Silk"
    {"brand": "彩多屋", "line": "Silk", "mat": "PLA Silk", "color": "黑色", "price": 25.10, "qty": 1},
    {"brand": "彩多屋", "line": "Silk", "mat": "PLA Silk", "color": "珍珠白", "price": 24.36, "qty": 1},
]

now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

for item in purchases:
    cur.execute("SELECT id FROM products WHERE brand=? AND product_line=? AND material=?", (item["brand"], item["line"], item["mat"]))
    p = cur.fetchone()
    if p:
        prod_id = p[0]
    else:
        prod_id = uuid.uuid4().hex
        cur.execute("INSERT INTO products (id, brand, product_line, material, notes, created_at) VALUES (?,?,?,?,?,?)",
            (prod_id, item["brand"], item["line"], item["mat"], "", now))
    
    cur.execute("SELECT id FROM colors WHERE product_id=? AND name=?", (prod_id, item["color"]))
    c = cur.fetchone()
    if c:
        col_id = c[0]
        cur.execute("UPDATE colors SET unopened = unopened + ? WHERE id=?", (item["qty"], col_id))
    else:
        col_id = uuid.uuid4().hex
        cur.execute("INSERT INTO colors (id, product_id, name, color_family, unopened, opened, notes) VALUES (?,?,?,?,?,?,?)",
            (col_id, prod_id, item["color"], "", item["qty"], 0, ""))
    
    cur.execute("INSERT INTO stock_ins (id, color_id, qty, unit_price, created_at) VALUES (?,?,?,?,?)",
        (uuid.uuid4().hex, col_id, item["qty"], item["price"], now))

conn.commit()
print("Success re-inserting correctly")

