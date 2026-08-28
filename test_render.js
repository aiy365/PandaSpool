
const fs = require("fs");
const data = JSON.parse(fs.readFileSync("products.json"));
function esc(s) { return s ? String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;") : ""; }
function yuan(n) { return "¥" + n; }
function productStock(p) {
  const all = p.colors || [];
  const shelf = all.filter((c) => c.unopened > 0 || c.opened > 0);
  return {
    all, shelf,
    unopened: shelf.reduce((n, c) => n + Number(c.unopened || 0), 0),
    opened: shelf.filter((c) => Number(c.opened || 0) > 0).length,
    catalog: all.length,
  };
}
function productCost(p) { return { avg: 10 }; }
function getDetailedColor() { return ["", false]; }
function stockChip(c) { return "CHIP"; }
function specStrip() { return "STRIP"; }

const rows = (data || []).map((p) => ({ p, s: productStock(p) }));
try {
    const html = rows.map(({ p, s }) => `
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
      </article>`).join("");
      console.log("Rendered length:", html.length);
} catch (e) {
    console.error(e);
}

