#!/usr/bin/env python3
"""Inbound stock from 耗材登记.xlsx. Unique catalog matches only. No new colors/products."""
import os
import sqlite3

DB = "/var/lib/printpilot/app.sqlite3"
BAK = "/var/lib/printpilot/app.sqlite3.bak-stock-20260819-hot"

# product_id, catalog name, sheet qty, sheet color label
# 整数 N → 未开封 N + 封；小数 N → 未开封 floor(N) + 开封 1。备注保留登记表原数。
APPLIES = [
    # 大简 PETG 哑光
    ("b1f2217bf4e1d27817c4ddfcc3c13bcf", "白色", 1.5, "白色"),
    ("b1f2217bf4e1d27817c4ddfcc3c13bcf", "灰色", 1, "灰色"),
    # 大简 PETG HF
    ("f3e1fd89c5e297d01ac2626517bb57fa", "白色", 1, "白色"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "灰色", 2, "灰色"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "透明绿", 1, "透明绿"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "拿铁色", 1, "拿铁色"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "透明紫", 1, "透明紫"),
    # 三绿 PLA+2.0
    ("70a7c4ee8bbda8fa599a6b2247929ddd", "瓷白色", 1, "瓷白"),
    ("70a7c4ee8bbda8fa599a6b2247929ddd", "黑色", 1, "黑色"),
    ("70a7c4ee8bbda8fa599a6b2247929ddd", "蓝", 2, "蓝色"),
    # 天威 PLA Basic（商品已建，色卡仅黑色）
    ("e67ce04e60e9c691325962ff0599a5f5", "黑色", 1, "黑色"),
    # Polymaker Panchroma PLA
    ("2d2ac091692cf7ac51a2a0f263f5c464", "白色", 2, "白色"),
    ("2d2ac091692cf7ac51a2a0f263f5c464", "红色", 1, "红色"),
    ("2d2ac091692cf7ac51a2a0f263f5c464", "紫色", 1, "紫色"),
    # Polymaker Panchroma Matte（原误挂 Marble）
    ("6ab0d72faae6d9994dc69dfdb06ab265", "棉花白", 3, "棉花白"),
    ("6ab0d72faae6d9994dc69dfdb06ab265", "碳墨黑", 3, "黑色"),
    ("6ab0d72faae6d9994dc69dfdb06ab265", "岩石灰", 1.3, "灰色"),
    ("6ab0d72faae6d9994dc69dfdb06ab265", "薄荷绿", 1, "薄荷绿"),
    ("6ab0d72faae6d9994dc69dfdb06ab265", "糖果粉", 1, "糖果粉"),
    # Polymaker PETG
    ("6138b9be8d4b4a5f67a05ffe9a8dc4b6", "白色", 2, "白色"),
    ("6138b9be8d4b4a5f67a05ffe9a8dc4b6", "银色", 1, "银色"),
    ("6138b9be8d4b4a5f67a05ffe9a8dc4b6", "电光蓝", 1, "电光蓝"),
    ("6138b9be8d4b4a5f67a05ffe9a8dc4b6", "绿色", 2, "绿色"),
    ("6138b9be8d4b4a5f67a05ffe9a8dc4b6", "紫色", 1, "紫色"),
    # 拓竹 PETG Basic
    ("a634408a318f50dcf5f56b0816ffbcd2", "白色", 1.5, "白色"),
    ("a634408a318f50dcf5f56b0816ffbcd2", "黑色", 0.5, "黑色"),
    ("a634408a318f50dcf5f56b0816ffbcd2", "灰色", 2, "灰色"),
    ("a634408a318f50dcf5f56b0816ffbcd2", "红色", 1.3, "红色"),
    ("a634408a318f50dcf5f56b0816ffbcd2", "黄色", 1.3, "黄色"),
    ("a634408a318f50dcf5f56b0816ffbcd2", "橙色", 1, "橙色"),
    # 拓竹 PLA Basic
    ("cb2f24e169f3e4fcec0159d60465fc63", "白色", 1.5, "白色"),
    ("cb2f24e169f3e4fcec0159d60465fc63", "红色", 0.5, "红色"),
]


def qty(n):
    opened = 1 if abs(float(n) - int(n)) > 1e-9 else 0
    return int(n), opened


db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
if os.path.exists(BAK):
    os.remove(BAK)
db.execute("VACUUM INTO ?", (BAK,))
print("hot backup ok")

# rename Panchroma Marble → Matte
cur = db.execute(
    "update products set product_line=?, material=? where id=?",
    ("Panchroma Matte", "PLA", "6ab0d72faae6d9994dc69dfdb06ab265"),
)
print("rename Panchroma Matte", cur.rowcount)

ok = 0
miss = []
for pid, cname, n, sheet in APPLIES:
    unopened, opened = qty(n)
    note = f"登记表 {sheet} {n}盘"
    r = db.execute(
        "select id,name,unopened,opened,notes from colors where product_id=? and name=?",
        (pid, cname),
    ).fetchone()
    if not r:
        miss.append((pid, cname, n, sheet))
        print("MISSING", pid[:8], cname, n)
        continue
    # 不覆盖架子上已有且数量不同的库存（R3D / 遇果不在本清单里）
    if (r["unopened"] or r["opened"]) and (r["unopened"] != unopened or r["opened"] != opened):
        print(
            f"SKIP-EXISTING {pid[:8]} {cname} keep {r['unopened']}+{'开' if r['opened'] else '封'} "
            f"not {unopened}+{'开' if opened else '封'}"
        )
        continue
    db.execute(
        "update colors set unopened=?, opened=?, notes=? where id=?",
        (unopened, opened, note, r["id"]),
    )
    print(f"OK {pid[:8]} {cname} <- {sheet} {n} => {unopened}+{'开' if opened else '封'}")
    ok += 1

db.commit()

# shelf summary
print("---SHELF---")
for r in db.execute(
    """
    select p.brand, p.product_line, p.material, c.name, c.unopened, c.opened
    from colors c join products p on p.id=c.product_id
    where c.unopened>0 or c.opened>0
    order by p.brand, p.product_line, c.name
    """
):
    print(dict(r))
print("applied", ok, "missing", len(miss))
db.close()
