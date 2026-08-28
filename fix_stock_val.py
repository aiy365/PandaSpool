
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_stock_render = """      <div class="stats stats-vertical lg:stats-horizontal shadow-sm bg-base-200 mt-3">
        <div class="stat py-3"><div class="stat-title">架子总盘</div><div class="stat-value text-primary text-3xl">${m.total}</div></div>
        <div class="stat py-3"><div class="stat-title">PLA 族</div><div class="stat-value text-3xl">${m.pla}</div><div class="stat-desc">含哑光 / Lite，丝绸单列</div></div>
        <div class="stat py-3"><div class="stat-title">PETG 族</div><div class="stat-value text-3xl">${m.petg}</div><div class="stat-desc">含高速 / 透 / 哑光</div></div>
      </div>"""

new_stock_render = """      <div class="stats stats-vertical lg:stats-horizontal shadow-sm bg-base-200 mt-3">
        <div class="stat py-3"><div class="stat-title">架子总盘</div><div class="stat-value text-primary text-3xl">${m.total}</div><div class="stat-desc font-bold mt-1 text-primary">总资产 ￥${list.reduce((acc, p) => acc + (p.colors||[]).reduce((cacc, c) => cacc + ((c.unopened||0)+(c.opened||0))*(c.avg_price||0), 0), 0).toFixed(0)}</div></div>
        <div class="stat py-3"><div class="stat-title">PLA 族</div><div class="stat-value text-3xl">${m.pla}</div><div class="stat-desc">含哑光 / Lite，丝绸单列<br>均价 ￥${(() => {
          let q=0, c=0;
          for(let p of list) if(materialBucket(p)==="PLA") { let x = productCost(p); q+=x.qty; c+=x.cost; }
          return q ? (c/q).toFixed(1) : "0";
        })()}</div></div>
        <div class="stat py-3"><div class="stat-title">PETG 族</div><div class="stat-value text-3xl">${m.petg}</div><div class="stat-desc">含高速 / 透 / 哑光<br>均价 ￥${(() => {
          let q=0, c=0;
          for(let p of list) if(materialBucket(p)==="PETG") { let x = productCost(p); q+=x.qty; c+=x.cost; }
          return q ? (c/q).toFixed(1) : "0";
        })()}</div></div>
      </div>"""

text = text.replace(old_stock_render, new_stock_render)
with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

