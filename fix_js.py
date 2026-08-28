import re
with open('live_app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Fetch presets globally or per page
# We can just fetch it in viewProduct
# 2. Add bambu_preset_id field
# 3. Save it
# 4. Check block in viewSpools intake logic

old_edit = """${field("品牌", inputEl("b", `value="${esc(p.brand)}" list="brand-list"`))}
        ${field("系列", inputEl("l", `value="${esc(p.product_line)}"`))}
        ${field("材质", selectEl("m", `<option></option>${MAT_ORDER.map((m) => `<option${p.material === m ? " selected" : ""}>${esc(m)}</option>`).join("")}`))}
        ${field("备注", inputEl("n", `value="${esc(p.notes)}"`))}"""

new_edit = """${field("品牌", inputEl("b", `value="${esc(p.brand)}" list="brand-list"`))}
        ${field("系列", inputEl("l", `value="${esc(p.product_line)}"`))}
        ${field("材质", selectEl("m", `<option></option>${MAT_ORDER.map((m) => `<option${p.material === m ? " selected" : ""}>${esc(m)}</option>`).join("")}`))}
        ${field("拓竹关联预设", selectEl("bpi", `<option value="">-- 同步后可关联真实预设 --</option>`))}
        ${field("备注", inputEl("n", `value="${esc(p.notes)}"`))}"""

js = js.replace(old_edit, new_edit)

old_save = """const payload = {
        brand: $("#b").value.trim(),
        product_line: $("#l").value.trim(),
        material: $("#m").value.trim(),
        notes: $("#n").value.trim(),
      };"""
new_save = """const payload = {
        brand: $("#b").value.trim(),
        product_line: $("#l").value.trim(),
        material: $("#m").value.trim(),
        bambu_preset_id: $("#bpi") ? $("#bpi").value : "",
        notes: $("#n").value.trim(),
      };"""
js = js.replace(old_save, new_save)

old_view = """try { data = await api("/api/products/" + id); }"""
new_view = """try { data = await api("/api/products/" + id); }"""
# Add dynamic loading of presets to viewProduct
inject_presets = """
  // Dynamically load presets
  api("/api/presets").then(presets => {
    const sel = $("#bpi");
    if (!sel) return;
    const current = data.product.bambu_preset_id || "";
    let html = `<option value="">-- 未关联 --</option>`;
    for (const pr of presets) {
      html += `<option value="${pr.id}" ${pr.id===current?"selected":""}>${esc(pr.name)}</option>`;
    }
    sel.innerHTML = html;
  }).catch(e => console.warn("Failed to load presets", e));
"""
# insert it right after render of viewProduct
# we can look for `$("#pe-save").onclick` and put it before
if "api(\"/api/presets\").then(presets => {" not in js:
    js = js.replace('$("#pe-save").onclick', inject_presets + '\n  $("#pe-save").onclick')


# Add the Sync button to settings page
old_settings = """${card(`
      <div class="row cols-2">"""
new_settings = """${card(`
      <div class="flex justify-between items-center mb-2">
        <h2 class="card-title m-0">拓竹云预设同步</h2>
        <button type="button" class="btn btn-secondary btn-sm" id="btn-sync-presets">抓取已有料盘作预设</button>
      </div>
      <p class="muted mb-4">因为拓竹没开放预设接口，你可以在拓竹APP里建一个库存并选上你的自定义预设，然后点此按钮，系统会自动“偷”下这些真实预设ID。</p>
      <div class="row cols-2">"""
if "拓竹云预设同步" not in js:
    js = js.replace(old_settings, new_settings)

sync_js = """
  if ($("#btn-sync-presets")) {
    $("#btn-sync-presets").onclick = (e) => busy(e.currentTarget, async () => {
      const res = await api("/api/presets/sync", { method: "POST" });
      toast(`成功抓取 ${res.length} 个拓竹预设`, "success");
    });
  }
"""
if "btn-sync-presets" not in js:
    js = js.replace('$("#sa").onclick = (e) => busy(e.currentTarget, async () => {', sync_js + '\n  $("#sa").onclick = (e) => busy(e.currentTarget, async () => {')


# Check intake blocking
old_intake = """const qty = parseInt($("#ik-qty").value);"""
new_intake = """const qty = parseInt($("#ik-qty").value);
    // CHECK PRESET
    // We need to fetch product info to see if preset is missing
    const prod = (list || []).find(p => (p.colors||[]).some(c => c.id === ikCid));
    if (prod && !prod.bambu_preset_id) {
       alert("该耗材尚未绑定拓竹预设！\\n请先进入该产品页，编辑并关联真实拓竹预设，否则无法同步到拓竹云。");
       return;
    }"""
js = js.replace(old_intake, new_intake)

with open('live_app.js', 'w', encoding='utf-8') as f:
    f.write(js)
print("Updated live_app.js with Preset logic")
