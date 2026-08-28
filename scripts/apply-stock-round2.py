#!/usr/bin/env python3
"""Round 2 inbound: user-picked catalog colors + authorized new products/colors."""
import os
import secrets
import sqlite3
from datetime import datetime, timezone

DB = "/var/lib/printpilot/app.sqlite3"
BAK = "/var/lib/printpilot/app.sqlite3.bak-stock-round2"

# 已有色卡：只改库存，不新建
# (product_id, catalog_name, qty, sheet_label)
EXISTING = [
    ("f3e1fd89c5e297d01ac2626517bb57fa", "米白色", 1, "珍珠白"),
    ("6ab0d72faae6d9994dc69dfdb06ab265", "日落橙", 1, "橙色"),
    ("6ab0d72faae6d9994dc69dfdb06ab265", "土壤棕", 1, "棕色"),
    ("6138b9be8d4b4a5f67a05ffe9a8dc4b6", "青色", 1, "薄荷绿/TEAL"),
    ("a634408a318f50dcf5f56b0816ffbcd2", "深蓝色", 1.3, "蓝色"),
]

# 已有商品上新建颜色
# (product_id, new_name, qty, sheet_label)
NEW_COLORS = [
    ("f3e1fd89c5e297d01ac2626517bb57fa", "深灰色", 1, "深灰"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "蓝色", 1, "蓝色"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "棕色", 1, "棕色"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "香芋紫", 1, "香芋色"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "肤色", 1, "肤色"),
    ("f3e1fd89c5e297d01ac2626517bb57fa", "桃红", 1, "桃红"),
]

# 新建商品 + 仅入库这一盘的色（不灌整张色卡）
# (brand, product_line, material, colors[(name, qty, sheet)])
NEW_PRODUCTS = [
    ("三绿", "Lite", "PLA Lite", [("柠檬黄", 1, "柠檬黄")]),
    ("三绿", "", "PETG", [("暗夜黑", 1, "黑色"), ("透明色", 1, "透明色")]),
    ("三绿", "Matte", "PLA Matte", [("橡木色", 1, "橡木色")]),
    ("彩多屋", "Silk", "PLA Silk", [("珍珠白", 1, "珍珠白"), ("黑色", 0.5, "黑色")]),
    ("拓竹", "Matte", "PLA Matte", [("骨白色", 1, "玉石白")]),
    ("拓竹", "Lite", "PLA Lite", [("绿色", 1, "绿色")]),
    ("必趣", "PLA GO", "PLA GO", [("牛油果色", 1, "牛油果色")]),
]


def qty(n):
    opened = 1 if abs(float(n) - int(n)) > 1e-9 else 0
    return int(n), opened


def family(name):
    rules = [
        (["蓝", "blue"], "蓝色系"),
        (["绿", "牛油果", "green"], "绿色系"),
        (["紫", "香芋", "purple", "violet"], "紫色系"),
        (["红", "粉", "桃", "rose", "pink", "red"], "红粉色系"),
        (["黄", "橙", "柠檬", "yellow", "orange"], "黄橙色系"),
        (["棕", "拿铁", "橡木", "咖啡", "肤", "米色", "brown", "beige"], "棕米色系"),
        (["金", "银", "铜", "metal", "gold", "silver"], "金属色系"),
        (["黑", "灰", "black", "gray", "grey"], "黑灰色系"),
        (["白", "white"], "白色系"),
        (["彩", "渐变", "虹", "多色", "rainbow", "multicolor"], "多色/效果色系"),
        (["透明", "自然", "clear", "transparent", "natural"], "透明/自然色系"),
    ]
    # 青色：商家 Teal，跟现有色卡一样归蓝色系
    if name == "青色":
        return "蓝色系"
    for aliases, fam in rules:
        for a in aliases:
            if a.lower() in name.lower() or a in name:
                return fam
    return "未分类"


def new_id():
    return secrets.token_hex(16)


def note_of(sheet, n):
    return f"登记表 {sheet} {n}盘"


db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
if os.path.exists(BAK):
    os.remove(BAK)
db.execute("VACUUM INTO ?", (BAK,))
print("hot backup ok")


def set_stock(pid, name, n, sheet, create=False):
    unopened, opened = qty(n)
    note = note_of(sheet, n)
    r = db.execute(
        "select id,name,unopened,opened from colors where product_id=? and name=?",
        (pid, name),
    ).fetchone()
    if not r:
        if not create:
            print("MISSING", pid[:8], name, n)
            return False
        cid = new_id()
        db.execute(
            "insert into colors(id,product_id,name,color_family,unopened,opened,notes) values(?,?,?,?,?,?,?)",
            (cid, pid, name, family(name), unopened, opened, note),
        )
        print(f"NEW-COLOR {pid[:8]} {name} <- {sheet} {n} => {unopened}+{'开' if opened else '封'} [{family(name)}]")
        return True
    if (r["unopened"] or r["opened"]) and (r["unopened"] != unopened or r["opened"] != opened):
        print(
            f"SKIP-EXISTING {pid[:8]} {name} keep {r['unopened']}+{'开' if r['opened'] else '封'} "
            f"not {unopened}+{'开' if opened else '封'}"
        )
        return False
    db.execute(
        "update colors set unopened=?, opened=?, notes=? where id=?",
        (unopened, opened, note, r["id"]),
    )
    print(f"OK {pid[:8]} {name} <- {sheet} {n} => {unopened}+{'开' if opened else '封'}")
    return True


ok = 0
for pid, cname, n, sheet in EXISTING:
    if set_stock(pid, cname, n, sheet, create=False):
        ok += 1

for pid, cname, n, sheet in NEW_COLORS:
    if set_stock(pid, cname, n, sheet, create=True):
        ok += 1

now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
for brand, line, material, colors in NEW_PRODUCTS:
    row = db.execute(
        "select id from products where brand=? and product_line=? and material=?",
        (brand, line, material),
    ).fetchone()
    if row:
        pid = row["id"]
        print(f"PRODUCT-EXISTS {pid[:8]} {brand}/{line}/{material}")
    else:
        pid = new_id()
        db.execute(
            "insert into products(id,brand,product_line,material,notes,created_at) values(?,?,?,?,?,?)",
            (pid, brand, line, material, "登记表补建，仅入库已有盘，未灌全色卡", now),
        )
        print(f"NEW-PRODUCT {pid[:8]} {brand}/{line}/{material}")
    for cname, n, sheet in colors:
        if set_stock(pid, cname, n, sheet, create=True):
            ok += 1

db.commit()
print("---SHELF---")
for r in db.execute(
    """
    select p.brand, p.product_line, p.material, c.name, c.unopened, c.opened, c.notes
    from colors c join products p on p.id=c.product_id
    where c.unopened>0 or c.opened>0
    order by p.brand, p.product_line, p.material, c.name
    """
):
    print(dict(r))
print("applied", ok)
db.close()
