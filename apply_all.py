
import sqlite3, uuid, datetime

conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()

purchases = [
    {"brand": "R3D", "line": "经济型", "mat": "PETG", "color": "透明色", "price": 28.32, "qty": 5},
    {"brand": "必趣", "line": "PLA GO", "mat": "PLA", "color": "牛油果色", "price": 30.00, "qty": 1},
    {"brand": "拓竹", "line": "Lite", "mat": "PLA", "color": "绿色", "price": 27.00, "qty": 1},
    {"brand": "拓竹", "line": "Matte", "mat": "PLA", "color": "骨白色", "price": 27.00, "qty": 1},
    {"brand": "彩多屋", "line": "Silk", "mat": "PLA", "color": "黑色", "price": 25.10, "qty": 1},
    {"brand": "彩多屋", "line": "Silk", "mat": "PLA", "color": "珍珠白", "price": 24.36, "qty": 1},
    {"brand": "三绿", "line": "Matte", "mat": "PLA", "color": "橡木色", "price": 25.30, "qty": 1},
    {"brand": "三绿", "line": "", "mat": "PETG", "color": "透明色", "price": 21.50, "qty": 1},
    {"brand": "三绿", "line": "", "mat": "PETG", "color": "暗夜黑", "price": 21.50, "qty": 1},
    {"brand": "三绿", "line": "Lite", "mat": "PLA", "color": "柠檬黄", "price": 30.00, "qty": 1},
    {"brand": "大简", "line": "HF", "mat": "PETG", "color": "拿铁色", "price": 15.60, "qty": 1},
    {"brand": "遇果", "line": "", "mat": "PETG", "color": "银色", "price": 13.71, "qty": 1},
    {"brand": "遇果", "line": "", "mat": "PETG", "color": "黑色", "price": 13.71, "qty": 7},
    {"brand": "大简", "line": "HF", "mat": "PETG", "color": "桃红", "price": 15.60, "qty": 1},
    {"brand": "大简", "line": "HF", "mat": "PETG", "color": "肤色", "price": 15.60, "qty": 1},
    {"brand": "大简", "line": "HF", "mat": "PETG", "color": "香芋紫", "price": 15.60, "qty": 1},
    {"brand": "大简", "line": "HF", "mat": "PETG", "color": "棕色", "price": 15.60, "qty": 1},
    {"brand": "大简", "line": "HF", "mat": "PETG", "color": "蓝色", "price": 15.60, "qty": 1},
    {"brand": "大简", "line": "HF", "mat": "PETG", "color": "深灰色", "price": 15.60, "qty": 1},
    {"brand": "天威", "line": "", "mat": "PLA", "color": "黑色", "price": 21.00, "qty": 1},
    
    {"brand": "POLYMAKER", "line": "高速PETG", "mat": "PETG", "color": "橙色", "price": 30.00, "qty": 1},
    {"brand": "POLYMAKER", "line": "高速PETG", "mat": "PETG", "color": "深绿色", "price": 30.00, "qty": 1},
    {"brand": "POLYMAKER", "line": "高速PETG", "mat": "PETG", "color": "黑色", "price": 30.00, "qty": 1},
    {"brand": "POLYMAKER", "line": "Panchroma", "mat": "PLA", "color": "黑色", "price": 25.80, "qty": 1},
    {"brand": "POLYMAKER", "line": "Panchroma", "mat": "PLA", "color": "棕色", "price": 25.80, "qty": 1},
    {"brand": "POLYMAKER", "line": "Panchroma", "mat": "PLA", "color": "钢铁灰", "price": 25.80, "qty": 1},
    {"brand": "POLYMAKER", "line": "Panchroma", "mat": "PLA", "color": "浅褐色", "price": 25.80, "qty": 1},
    {"brand": "三绿SUNLU", "line": "PLA+ 2.0", "mat": "PLA", "color": "咖棕色 (无线盘)", "price": 30.00, "qty": 1},
    {"brand": "三绿SUNLU", "line": "PLA+ 2.0", "mat": "PLA", "color": "橡木色 (无线盘)", "price": 30.00, "qty": 1},
    {"brand": "三慈", "line": "哑光", "mat": "PLA", "color": "黑色", "price": 20.90, "qty": 1},
    {"brand": "淘工厂", "line": "通用", "mat": "PLA", "color": "白色", "price": 13.90, "qty": 1},
    {"brand": "天天特卖工厂", "line": "通用", "mat": "PLA", "color": "白色 (无线盘)", "price": 13.43, "qty": 1},
    {"brand": "余兄弟", "line": "基础", "mat": "PETG", "color": "白色 (无料盘)", "price": 23.00, "qty": 1},
    {"brand": "余兄弟", "line": "基础", "mat": "PETG", "color": "白色 (有料盘)", "price": 26.00, "qty": 1},
    {"brand": "遇果科技", "line": "遇果2号", "mat": "PLA", "color": "灰色", "price": 21.00, "qty": 1},
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

cur.execute("UPDATE products SET brand=\"遇果\" WHERE brand IN (\"淘工厂\", \"天天特卖工厂\", \"遇果科技\")")
cur.execute("UPDATE products SET brand=\"三绿\" WHERE brand=\"三绿SUNLU\"")

cur.execute("SELECT id FROM products WHERE brand=\"POLYMAKER\" AND product_line=\"Panchroma\"")
new_panchroma = cur.fetchone()
cur.execute("SELECT id FROM products WHERE brand=\"Polymaker\" AND product_line=\"Panchroma\"")
old_panchroma = cur.fetchone()
if new_panchroma and old_panchroma:
    cur.execute("UPDATE colors SET product_id=? WHERE product_id=?", (old_panchroma[0], new_panchroma[0]))
    cur.execute("DELETE FROM products WHERE id=?", (new_panchroma[0],))
cur.execute("UPDATE products SET brand=\"Polymaker\" WHERE brand=\"POLYMAKER\"")

conn.commit()
print("Success")

