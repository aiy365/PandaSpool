
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_sum = """    const rolls = rows.reduce((n, r) => n + r.s.unopened, 0);
    const opened = rows.reduce((n, r) => n + r.s.opened, 0);
    $("#invsum").textContent = filter === "shelf"
      ? `架子 ${rows.length} 个料 · ${rolls} 卷未开封 · ${opened} 色有开封`
      : `产品 ${rows.length} 个 · 其中架子 ${rows.filter((r) => r.s.shelf.length).length} 个`;"""

new_sum = """    const rolls = rows.reduce((n, r) => n + r.s.unopened, 0);
    const opened = rows.reduce((n, r) => n + r.s.opened, 0);
    
    // Calculate Total Value & Average Price by Material
    let totalShelfValue = 0;
    const matStats = {};
    for (const { p, s } of rows) {
      const bkt = materialBucket(p);
      if (!matStats[bkt]) matStats[bkt] = { qty: 0, cost: 0 };
      const pc = productCost(p);
      matStats[bkt].qty += pc.qty;
      matStats[bkt].cost += pc.cost;
      
      for (const c of p.colors || []) {
        if ((c.unopened || 0) + (c.opened || 0) > 0) {
          totalShelfValue += ((c.unopened || 0) + (c.opened || 0)) * (c.avg_price || 0);
        }
      }
    }
    
    let avgStrs = [];
    for (const [mat, st] of Object.entries(matStats)) {
      if (st.qty > 0) avgStrs.push(`${mat}均价 ￥${(st.cost / st.qty).toFixed(1)}`);
    }
    
    $("#invsum").innerHTML = (filter === "shelf"
      ? `架子 ${rows.length} 个料 · ${rolls} 卷未开封 · ${opened} 色有开封`
      : `产品 ${rows.length} 个 · 其中架子 ${rows.filter((r) => r.s.shelf.length).length} 个`)
      + (totalShelfValue > 0 ? ` · <span class="text-primary font-bold">库存总价值 ￥${totalShelfValue.toFixed(1)}</span>` : "")
      + (avgStrs.length > 0 ? ` <span class="muted text-xs" style="margin-left:1rem">(${avgStrs.join(" / ")})</span>` : "");
"""

text = text.replace(old_sum, new_sum)
with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

