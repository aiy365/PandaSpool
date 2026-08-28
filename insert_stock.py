
import sqlite3, uuid, datetime

items = [
    # Polymaker 高速PETG
    {"brand": "POLYMAKER", "line": "高速PETG", "mat": "PETG", "color": "橙色", "price": 26.97},
    {"brand": "POLYMAKER", "line": "高速PETG", "mat": "PETG", "color": "深绿色", "price": 26.96},
    {"brand": "POLYMAKER", "line": "高速PETG", "mat": "PETG", "color": "黑色", "price": 26.91},
    # Polymaker Panchroma PLA
    {"brand": "POLYMAKER", "line": "Panchroma", "mat": "PLA", "color": "黑色", "price": 27.45},
    {"brand": "POLYMAKER", "line": "Panchroma", "mat": "PLA", "color": "棕色", "price": 27.44},
    {"brand": "POLYMAKER", "line": "Panchroma", "mat": "PLA", "color": "钢铁灰", "price": 27.72},
    {"brand": "POLYMAKER", "line": "Panchroma", "mat": "PLA", "color": "浅褐色", "price": 27.33},
    # SUNLU PLA+ 2.0
    {"brand": "三绿SUNLU", "line": "PLA+ 2.0", "mat": "PLA+", "color": "咖棕色 (无线盘)", "price": 30.90},
    {"brand": "三绿SUNLU", "line": "PLA+ 2.0", "mat": "PLA+", "color": "橡木色 (无线盘)", "price": 30.90},
    # 三慈
    {"brand": "三慈", "line": "哑光", "mat": "PLA", "color": "黑色", "price": 22.86},
    # 淘工厂 Generic
    {"brand": "淘工厂", "line": "通用", "mat": "PETG", "color": "白色", "price": 15.01},
    # 天天特卖
    {"brand": "天天特卖工厂", "line": "通用", "mat": "PETG", "color": "白色 (无线盘)", "price": 13.96},
    # 余兄弟
    {"brand": "余兄弟", "line": "基础", "mat": "PETG", "color": "白色 (无料盘)", "price": 13.90},
    {"brand": "余兄弟", "line": "基础", "mat": "PETG", "color": "白色 (有料盘)", "price": 9.90},
    # 遇果科技
    {"brand": "遇果科技", "line": "遇果2号", "mat": "PLA", "color": "灰色", "price": 21.00},
]

conn = sqlite3.connect("data/app.sqlite3")
cur = conn.cursor()

def new_id(): return uuid.uuid4().hex

now = datetime.datetime.utcnow().isoformat() + "Z"

for item in items:
    # 1. Product
    cur.execute("SELECT id FROM products WHERE brand=? AND product_line=? AND material=?", (item["brand"], item["line"], item["mat"]))
    row = cur.fetchone()
    if row:
        prod_id = row[0]
    else:
        prod_id = new_id()
        cur.execute("INSERT INTO products (id, brand, product_line, material, notes, created_at) VALUES (?,?,?,?,?,?)", 
            (prod_id, item["brand"], item["line"], item["mat"], "", now))
    
    # 2. Color
    cur.execute("SELECT id, unopened FROM colors WHERE product_id=? AND name=?", (prod_id, item["color"]))
    row = cur.fetchone()
    if row:
        col_id = row[0]
        unopened = row[1] + 1
        cur.execute("UPDATE colors SET unopened=? WHERE id=?", (unopened, col_id))
    else:
        col_id = new_id()
        cur.execute("INSERT INTO colors (id, product_id, name, color_family, unopened, opened, notes) VALUES (?,?,?,?,?,?,?)",
            (col_id, prod_id, item["color"], "", 1, 0, ""))
            
    # 3. Stock In
    cur.execute("INSERT INTO stock_ins (id, color_id, qty, unit_price, note, created_at) VALUES (?,?,?,?,?,?)",
        (new_id(), col_id, 1.0, item["price"], "自动录入: 实付款", now))

conn.commit()
print("All items inserted successfully!")

