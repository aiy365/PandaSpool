
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_func = """function familyStackBar(label, n, max, famCounts) {
  const pct = n ? Math.max(8, Math.round((n / max) * 100)) : 0;
  const known = FAMILY_ORDER.filter((f) => famCounts?.[f] > 0);
  const extra = Object.keys(famCounts || {}).filter((f) => !FAMILY_ORDER.includes(f) && famCounts[f] > 0);
  const segs = known.concat(extra).map((f) => {
    const w = n ? (famCounts[f] / n) * 100 : 0;
    const light = LIGHT_FAM.has(f) ? " is-light" : "";
    return `<span class="stk-seg${light}" style="width:${w}%;background:${FAMILY_COLOR[f] || "#94a3b8"}" title="${esc(f)}"></span>`;
  }).join("");
  return `<button type="button" class="stk-bar stk-bar-btn" data-fam="" data-bkt="${esc(label)}" title="只看 ${esc(label)}">
    <span class="stk-bar-lab">${esc(label)}</span>
    <span class="stk-track"><span class="stk-fill" style="width:${pct}%">${segs}</span></span>
    <b>${n}</b>
  </button>`;
}"""

new_func = """function familyStackBar(label, n, max, famCounts, avgPInfo) {
  const pct = n ? Math.max(8, Math.round((n / max) * 100)) : 0;
  const known = FAMILY_ORDER.filter((f) => famCounts?.[f] > 0);
  const extra = Object.keys(famCounts || {}).filter((f) => !FAMILY_ORDER.includes(f) && famCounts[f] > 0);
  const segs = known.concat(extra).map((f) => {
    const w = n ? (famCounts[f] / n) * 100 : 0;
    const light = LIGHT_FAM.has(f) ? " is-light" : "";
    return `<span class="stk-seg${light}" style="width:${w}%;background:${FAMILY_COLOR[f] || "#94a3b8"}" title="${esc(f)}"></span>`;
  }).join("");
  let avgText = "";
  if (avgPInfo && avgPInfo.q > 0) {
    avgText = ` <span class="muted text-xs font-normal ml-1" style="opacity:0.7">(均价￥${(avgPInfo.c / avgPInfo.q).toFixed(1)})</span>`;
  }
  return `<button type="button" class="stk-bar stk-bar-btn" data-fam="" data-bkt="${esc(label)}" title="只看 ${esc(label)}">
    <span class="stk-bar-lab whitespace-nowrap">${esc(label)}${avgText}</span>
    <span class="stk-track"><span class="stk-fill" style="width:${pct}%">${segs}</span></span>
    <b>${n}</b>
  </button>`;
}"""
text = text.replace(old_func, new_func)

old_call = """${card(`<h2 class="card-title text-base">按材料</h2>${m.buckets.map((b) => familyStackBar(b, m.colSum[b] || 0, maxBkt, m.famByBucket[b] || {})).join("")}`)}"""
new_call = """${(() => {
    const avgP = {};
    for (let p of list || []) {
      let b = materialBucket(p);
      if (!avgP[b]) avgP[b] = {q:0,c:0};
      let x = productCost(p);
      avgP[b].q += x.qty;
      avgP[b].c += x.cost;
    }
    return card(`<h2 class="card-title text-base">按材料</h2>${m.buckets.map((b) => familyStackBar(b, m.colSum[b] || 0, maxBkt, m.famByBucket[b] || {}, avgP[b])).join("")}`);
})()}"""
text = text.replace(old_call, new_call)

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

