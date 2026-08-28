import re

with open('live_app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Replace the edit product form
old_form = """${field("品牌", inputEl("b", `value="${esc(p.brand)}" list="brand-list"`))}
        ${field("系列", inputEl("l", `value="${esc(p.product_line)}"`))}
        ${field("材质", selectEl("m", `<option></option>${MAT_ORDER.map((m) => `<option${p.material === m ? " selected" : ""}>${esc(m)}</option>`).join("")}`))}
        ${field("拓竹关联预设", selectEl("bpi", `<option value="">-- 同步后可关联真实预设 --</option>`))}
        ${field("备注", inputEl("n", `value="${esc(p.notes)}"`))}"""

new_form = """${field("关联官方预设", selectEl("bpi", `<option value="">-- 请先抓取并选择底层预设 --</option>`))}
        ${field("品牌 (自动锁定)", inputEl("b", `value="${esc(p.brand)}" readonly class="input input-bordered w-full bg-base-200"`))}
        ${field("材质 (自动锁定)", inputEl("m", `value="${esc(p.material)}" readonly class="input input-bordered w-full bg-base-200"`))}
        ${field("细分系列", inputEl("l", `value="${esc(p.product_line)}" placeholder="如：哑光 / 渐变 (选填)"`))}
        ${field("备注", inputEl("n", `value="${esc(p.notes)}"`))}"""
js = js.replace(old_form, new_form)

# Add onchange listener for presets
old_presets_js = """let html = `<option value="">-- 未关联 --</option>`;
    for (const pr of presets) {
      html += `<option value="${pr.id}" ${pr.id===current?"selected":""}>${esc(pr.name)}</option>`;
    }
    sel.innerHTML = html;
  }).catch(e => console.warn("Failed to load presets", e));"""

new_presets_js = """let html = `<option value="">-- 未关联 --</option>`;
    for (const pr of presets) {
      html += `<option value="${pr.id}" ${pr.id===current?"selected":""}>${esc(pr.name)}</option>`;
    }
    sel.innerHTML = html;
    
    sel.onchange = (e) => {
      const pr = presets.find(x => x.id === e.target.value);
      if (pr) {
        $("#b").value = pr.vendor;
        $("#m").value = pr.material;
      }
    };
  }).catch(e => console.warn("Failed to load presets", e));"""
js = js.replace(old_presets_js, new_presets_js)

with open('live_app.js', 'w', encoding='utf-8') as f:
    f.write(js)
