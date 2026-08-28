
import re

with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_stat = """<div class="stat py-3"><div class="stat-title">架子总盘</div><div class="stat-value text-primary text-3xl">${m.total}</div></div>"""
new_stat = """<div class="stat py-3"><div class="stat-title">架子总盘</div><div class="stat-value text-primary text-3xl">${m.total}</div><div class="stat-desc font-bold mt-1 text-primary">总资产 ￥${list.reduce((acc, p) => acc + (p.colors||[]).reduce((cacc, c) => cacc + ((c.unopened||0)+(c.opened||0))*(c.avg_price||0), 0), 0).toFixed(0)}</div></div>"""

if old_stat in text:
    text = text.replace(old_stat, new_stat)
    with open("web/dist/app.js", "w", encoding="utf-8") as f:
        f.write(text)
    print("Patched successfully!")
else:
    print("Could not find the exact string to replace!")

