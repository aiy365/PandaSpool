#!/usr/bin/env python3
"""补记登记表单价（不加库存）并确认全部草稿。"""
import secrets
import sqlite3
from datetime import datetime, timezone

DB = "/var/lib/printpilot/app.sqlite3"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
SKIP = False

# product_id, color name, 表内盘数, 表内单价
ITEMS = [
    ("b1f2217bf4e1d27817c4ddfcc3c13bcf", "白色", 1.5, 21.58, "登记表 大简 PETG 哑光"),
    ("b1f2217bf4e1d27817c4ddfcc3c13bcf", "灰色", 1, 21.58, "登记表 大简 PETG 哑光"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "白色", 1, 15.6, "登记表 大简 PETG"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "灰色", 2, 15.6, "登记表 大简 PETG"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "透明绿", 1, 15.6, "登记表 大简 PETG"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "拿铁色", 1, 15.6, "登记表 大简 PETG"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "透明紫", 1, 15.6, "登记表 大简 PETG"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "米白色", 1, 15.6, "登记表 大简 PETG"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "深灰色", 1, 15.6, "登记表 大简 PETG"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "蓝色", 1, 15.6, "登记表 大简 PETG"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "棕色", 1, 15.6, "登记表 大简 PETG"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "香芋紫", 1, 15.6, "登记表 大简 PETG"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "肤色", 1, 15.6, "登记表 大简 PETG"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "桃红", 1, 15.6, "登记表 大简 PETG"),
    ("e67ce04e60e9c691325962ff0599a5f5", "黑色", 1, 21, "登记表 天威 PLA"),
    ("70a7c4ee8bbda8fa599a6b2247929ddd", "瓷白色", 1, 30, "登记表 三绿 PLA+2.0"),
    ("70a7c4ee8bbda8fa599a6b2247929ddd", "黑色", 1, 30, "登记表 三绿 PLA+2.0"),
    ("70a7c4ee8bbda8fa599a6b2247929ddd", "蓝", 2, 30, "登记表 三绿 PLA+2.0"),
    ("6349f9b0ae8696a26a7db1d8f39b86d8", "柠檬黄", 1, 30, "登记表 三绿 PLA+2.0 列，现挂 Lite"),
    ("745780ecb4aea8e654f012318dab8972", "暗夜黑", 1, 21.54, "登记表 三绿 PETG"),
    ("745780ecb4aea8e654f012318dab8972", "透明色", 1, 21.54, "登记表 三绿 PETG"),
    ("26fbf5e0f6e3b14d236b8d35dabace62", "橡木色", 1, 25.26, "登记表 三绿 PLA 哑光"),
    ("cd36d2dd888f9872e820a19be730d15b", "珍珠白", 1, 24.7, "登记表 彩多屋 PLA 丝绸"),
    ("cd36d2dd888f9872e820a19be730d15b", "黑色", 0.5, 24.7, "登记表 彩多屋 PLA 丝绸"),
    ("2d2ac091692cf7ac51a2a0f263f5c464", "白色", 2, 25.79, "登记表 Polymaker PLA"),
    ("2d2ac091692cf7ac51a2a0f263f5c464", "红色", 1, 25.79, "登记表 Polymaker PLA"),
    ("2d2ac091692cf7ac51a2a0f263f5c464", "紫色", 1, 25.79, "登记表 Polymaker PLA"),
    ("6ab0d72faae6d9994dc69dfdb06ab265", "棉花白", 3, 32, "登记表 Poly PLA 哑光"),
    ("6ab0d72faae6d9994dc69dfdb06ab265", "碳墨黑", 3, 32, "登记表 Poly PLA 哑光"),
    ("6ab0d72faae6d9994dc69dfdb06ab265", "岩石灰", 1.3, 32, "登记表 Poly PLA 哑光"),
    ("6ab0d72faae6d9994dc69dfdb06ab265", "薄荷绿", 1, 32, "登记表 Poly PLA 哑光"),
    ("6ab0d72faae6d9994dc69dfdb06ab265", "糖果粉", 1, 32, "登记表 Poly PLA 哑光"),
    ("6ab0d72faae6d9994dc69dfdb06ab265", "日落橙", 1, 32, "登记表 Poly PLA 哑光"),
    ("6ab0d72faae6d9994dc69dfdb06ab265", "土壤棕", 1, 32, "登记表 Poly PLA 哑光"),
    ("6138b9be8d4b4a5f67a05ffe9a8dc4b6", "白色", 2, 23, "登记表 Poly PETG"),
    ("6138b9be8d4b4a5f67a05ffe9a8dc4b6", "银色", 1, 23, "登记表 Poly PETG"),
    ("6138b9be8d4b4a5f67a05ffe9a8dc4b6", "电光蓝", 1, 23, "登记表 Poly PETG"),
    ("6138b9be8d4b4a5f67a05ffe9a8dc4b6", "绿色", 2, 23, "登记表 Poly PETG"),
    ("6138b9be8d4b4a5f67a05ffe9a8dc4b6", "紫色", 1, 23, "登记表 Poly PETG"),
    ("6138b9be8d4b4a5f67a05ffe9a8dc4b6", "青色", 1, 23, "登记表 Poly PETG"),
    ("a634408a318f50dcf5f56b0816ffbcd2", "白色", 1.5, 26.5, "登记表 拓竹PETG"),
    ("a634408a318f50dcf5f56b0816ffbcd2", "黑色", 0.5, 26.5, "登记表 拓竹PETG"),
    ("a634408a318f50dcf5f56b0816ffbcd2", "灰色", 2, 26.5, "登记表 拓竹PETG"),
    ("a634408a318f50dcf5f56b0816ffbcd2", "深蓝色", 1.3, 26.5, "登记表 拓竹PETG"),
    ("a634408a318f50dcf5f56b0816ffbcd2", "红色", 1.3, 26.5, "登记表 拓竹PETG"),
    ("a634408a318f50dcf5f56b0816ffbcd2", "黄色", 1.3, 26.5, "登记表 拓竹PETG"),
    ("a634408a318f50dcf5f56b0816ffbcd2", "橙色", 1, 26.5, "登记表 拓竹PETG"),
    ("cb2f24e169f3e4fcec0159d60465fc63", "白色", 1.5, 27, "登记表 拓竹PLA"),
    ("cb2f24e169f3e4fcec0159d60465fc63", "红色", 0.5, 27, "登记表 拓竹PLA"),
    ("dccccccf8f4c5dfc32cb0770db448d00", "骨白色", 1, 27, "登记表 拓竹PLA 玉石白，现挂 Matte"),
    ("4e13903217d281cbc482ee5182c40276", "绿色", 1, 27, "登记表 拓竹PLA，现挂 Lite"),
    ("4fdb4d60e64e0f3dfdef75f883ad4a58", "牛油果色", 1, 30, "登记表 必趣PLA"),
]

db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
ok = 0
miss = []
skip = 0
for pid, name, qty, price, note in ITEMS:
    c = db.execute("select id from colors where product_id=? and name=?", (pid, name)).fetchone()
    if not c:
        miss.append((pid[:8], name))
        print("MISS", pid[:8], name)
        continue
    exists = db.execute("select count(*) n from stock_ins where color_id=?", (c["id"],)).fetchone()["n"]
    if exists:
        skip += 1
        print("SKIP", name, "already has", exists)
        continue
    db.execute(
        "insert into stock_ins(id,color_id,qty,unit_price,note,created_at) values(?,?,?,?,?,?)",
        (secrets.token_hex(16), c["id"], qty, price, note, NOW),
    )
    print(f"OK {name} {qty}盘 @{price}")
    ok += 1

n = db.execute("update claims set status='confirmed' where status='draft'").rowcount
db.commit()
print("priced", ok, "skip", skip, "miss", len(miss), "confirmed_drafts", n)
print("drafts_left", db.execute("select count(*) from claims where status='draft'").fetchone()[0])
print("avg_sample")
for r in db.execute(
    """
    select p.brand, p.material, c.name, round(sum(s.qty*s.unit_price)/sum(s.qty),2) avg, sum(s.qty) qty
    from stock_ins s join colors c on c.id=s.color_id join products p on p.id=c.product_id
    group by c.id order by p.brand, c.name limit 20
    """
):
    print(dict(r))
db.close()
