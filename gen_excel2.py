
import sqlite3
import pandas as pd

conn = sqlite3.connect("prod.sqlite3")
query = """
SELECT 
    c.id as cid,
    p.brand AS "品牌",
    p.product_line AS "系列",
    p.material AS "材料",
    c.name AS "颜色",
    c.unopened AS "未开封数",
    c.opened AS "已拆封数"
FROM colors c
JOIN products p ON c.product_id = p.id
WHERE c.unopened > 0 OR c.opened > 0
ORDER BY p.brand, p.material, p.product_line, c.name
"""
df = pd.read_sql_query(query, conn)

# get all stock_ins
ins = pd.read_sql_query("SELECT color_id, qty, unit_price FROM stock_ins", conn)

def get_avg_price(cid):
    recs = ins[ins["color_id"] == cid]
    total_qty = recs["qty"].sum()
    if total_qty > 0:
        return (recs["qty"] * recs["unit_price"]).sum() / total_qty
    return 0

df["单卷均价(元)"] = df["cid"].apply(get_avg_price).round(2)
df["合计盘数"] = df["未开封数"] + df["已拆封数"]
df["资产小计(元)"] = (df["合计盘数"] * df["单卷均价(元)"]).round(2)

df = df.drop(columns=["cid"])

total_unopened = df["未开封数"].sum()
total_opened = df["已拆封数"].sum()
total_qty = df["合计盘数"].sum()
total_value = df["资产小计(元)"].sum()

grand_total = pd.DataFrame([{
    "品牌": "【总计】",
    "未开封数": total_unopened,
    "已拆封数": total_opened,
    "合计盘数": total_qty,
    "资产小计(元)": total_value
}])

df = pd.concat([df, grand_total], ignore_index=True)

out_path = r"C:\Users\user\.gemini\antigravity\brain\0b17df1d-4aef-4f93-b5a4-74a851741c5c\scratch\PrintPilot_Inventory.xlsx"
df.to_excel(out_path, index=False)
print("Excel saved to:", out_path)
print("Total value calculated in Python:", total_value)

