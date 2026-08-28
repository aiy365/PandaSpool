
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

# Replace the mapping logic
old_render = """    $("#list").innerHTML = rows.map(({ p, s }) => `
      <article class="inv-card card bg-base-100 shadow-sm border border-base-300 cursor-pointer" data-id="${p.id}">
        <div class="card-body inv-card-body">
          <div class="inv-card-top">
            <h2 class="inv-title">${esc(p.brand)} <span class="inv-line">${esc(p.product_line || "")}</span></h2>
            <span class="badge badge-ghost">${esc(p.material)}</span>
          </div>
          <div class="inv-stats">
            <span><b>${s.unopened}</b> 未开封</span>
            <span><b>${s.opened}</b> 色开封</span>
            <span class="muted">色卡 ${s.catalog}</span>
            ${productCost(p).avg ? `<span>均价 <b>${yuan(productCost(p).avg)}</b></span>` : ""}
          </div>
          ${specStrip(p.card)}
          <div class="inv-chips">
            ${s.shelf.length ? s.shelf.map(stockChip).join("") : `<span class="muted text-sm">架子上没有卷</span>`}
          </div>
        </div>
      </article>`).join("");"""

new_render = """    const grouped = {};
    rows.forEach(r => {
      if (!grouped[r.p.brand]) grouped[r.p.brand] = [];
      grouped[r.p.brand].push(r);
    });
    $("#list").innerHTML = Object.entries(grouped).map(([brandName, grp]) => `
      <div style="break-inside: avoid; margin-bottom: 1rem;">
        ${grp.map(({ p, s }) => `
          <article class="inv-card card bg-base-100 shadow-sm border border-base-300 cursor-pointer" style="margin-bottom: 0.75rem;" data-id="${p.id}">
            <div class="card-body inv-card-body">
              <div class="inv-card-top">
                <h2 class="inv-title">${esc(p.brand)} <span class="inv-line">${esc(p.product_line || "")}</span></h2>
                <span class="badge badge-ghost">${esc(p.material)}</span>
              </div>
              <div class="inv-stats">
                <span><b>${s.unopened}</b> 未开封</span>
                <span><b>${s.opened}</b> 色开封</span>
                <span class="muted">色卡 ${s.catalog}</span>
                ${productCost(p).avg ? `<span>均价 <b>${yuan(productCost(p).avg)}</b></span>` : ""}
              </div>
              ${specStrip(p.card)}
              <div class="inv-chips">
                ${s.shelf.length ? s.shelf.map(stockChip).join("") : `<span class="muted text-sm">架子上没有卷</span>`}
              </div>
            </div>
          </article>
        `).join("")}
      </div>
    `).join("");"""

text = text.replace(old_render, new_render)

# Remove the .inv-card break-inside from styles.css since we handle it in inline style of the wrapper
with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

