
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

# Replace the HTML generation in viewMaterials
old_render = """    const grouped = {};
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

new_render = """    // Masonry distribution by brand
    const grouped = {};
    rows.forEach(r => {
      if (!grouped[r.p.brand]) grouped[r.p.brand] = [];
      grouped[r.p.brand].push(r);
    });
    
    // Sort brands by how many items they have (largest first) so they pack nicely
    const brandsList = Object.entries(grouped).sort((a, b) => b[1].length - a[1].length);
    
    // Create 6 columns
    const numCols = Math.min(6, Math.max(1, Math.floor(window.innerWidth / 300))); // responsive columns
    const cols = Array.from({length: numCols}, () => []);
    const colHeights = Array.from({length: numCols}, () => 0);
    
    brandsList.forEach(([brandName, grp]) => {
      // Find the shortest column
      let minH = Math.min(...colHeights);
      let idx = colHeights.indexOf(minH);
      // Each item roughly counts as 1 unit of height, plus brand margin
      colHeights[idx] += grp.length;
      
      const html = `
        <div class="brand-group" style="margin-bottom: 1.5rem;">
          <h3 style="font-size: 0.85rem; font-weight: bold; color: #888; margin-bottom: 0.5rem; padding-left: 0.25rem;">${esc(brandName)}</h3>
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
      `;
      cols[idx].push(html);
    });
    
    $("#list").innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(${numCols}, minmax(0, 1fr)); gap: 1rem; align-items: start;">
        ${cols.map(c => `<div>${c.join("")}</div>`).join("")}
      </div>
    `;
    // We override styles.css grid by using inline display: grid on the wrapper, 
    // and we must remove column-count from .inv-list just in case
    $("#list").style.columnCount = "auto";
"""

text = text.replace(old_render, new_render)
with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

