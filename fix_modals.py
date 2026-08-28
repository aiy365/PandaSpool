import re

with open('live_app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Add Dialogs HTML to renderApp
dialogs_html = """
    <main class="page px-2 lg:px-4 max-w-7xl mx-auto" id="page"></main>
    
    <!-- Modals -->
    <dialog id="modal-danger" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg text-error">高危操作确认</h3>
        <p class="py-4" id="modal-danger-msg">确定执行此操作吗？</p>
        <div class="modal-action">
          <form method="dialog"><button class="btn">取消</button></form>
          <button class="btn btn-error" id="modal-danger-confirm">确定执行</button>
        </div>
      </div>
    </dialog>

    <dialog id="modal-weight" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg">修改料盘重量</h3>
        <div class="py-4">
          <label class="label"><span class="label-text">当前重量 (g)</span></label>
          <input type="number" id="modal-weight-input" class="input input-bordered w-full" />
          <input type="range" id="modal-weight-slider" class="range range-primary mt-4" step="10" />
        </div>
        <div class="modal-action">
          <form method="dialog"><button class="btn">取消</button></form>
          <button class="btn btn-primary" id="modal-weight-save">同步云端</button>
        </div>
      </div>
    </dialog>

    <dialog id="modal-intake" class="modal">
      <div class="modal-box overflow-visible">
        <h3 class="font-bold text-lg">料盘入库</h3>
        <div class="py-4 flex flex-col gap-4">
          <div class="form-control w-full">
            <label class="label"><span class="label-text">选择耗材规格 (仅上架产品)</span></label>
            <select id="modal-intake-color" class="select select-bordered w-full"></select>
          </div>
          <div class="form-control w-full">
            <label class="label"><span class="label-text">入库盘数</span></label>
            <div class="join">
              <button class="btn join-item" onclick="document.getElementById('modal-intake-qty').stepDown()">-</button>
              <input type="number" id="modal-intake-qty" class="input input-bordered join-item w-full text-center" value="1" min="1" max="100" />
              <button class="btn join-item" onclick="document.getElementById('modal-intake-qty').stepUp()">+</button>
            </div>
          </div>
        </div>
        <div class="modal-action">
          <form method="dialog"><button class="btn">取消</button></form>
          <button class="btn btn-primary" id="modal-intake-submit">确认入库</button>
        </div>
      </div>
    </dialog>
"""

content = content.replace('<main class="page px-2 lg:px-4 max-w-7xl mx-auto" id="page"></main>', dialogs_html)

# Add window functions at the bottom of the file
window_funcs = """

// ---- Global Modals Handlers ----
window.confirmDanger = (msg, onConfirm) => {
  document.getElementById('modal-danger-msg').innerText = msg;
  const btn = document.getElementById('modal-danger-confirm');
  btn.onclick = () => {
    document.getElementById('modal-danger').close();
    onConfirm();
  };
  document.getElementById('modal-danger').showModal();
};

window.editWeight = (spoolId, currentW, maxW) => {
  const input = document.getElementById('modal-weight-input');
  const slider = document.getElementById('modal-weight-slider');
  const saveBtn = document.getElementById('modal-weight-save');
  
  input.value = currentW;
  slider.max = maxW;
  slider.value = currentW;
  
  input.oninput = () => { slider.value = input.value; };
  slider.oninput = () => { input.value = slider.value; };
  
  saveBtn.onclick = async () => {
    saveBtn.disabled = true;
    const val = parseInt(input.value, 10);
    try {
      await api("/api/spools/" + spoolId + "/weight", { method: "PUT", body: { net_weight_g: val } });
      toast("重量已同步至拓竹云端", "success");
      document.getElementById('modal-weight').close();
      if (location.hash === '#/spools') window.onhashchange();
    } catch (ex) {
      toast(ex.message, "error");
    } finally {
      saveBtn.disabled = false;
    }
  };
  
  document.getElementById('modal-weight').showModal();
};

window.showIntakeModal = (preselectColorId = null) => {
  const sel = document.getElementById('modal-intake-color');
  sel.innerHTML = '';
  
  // Build options
  const onShelf = (window.products || []).filter(p => !p.draft);
  const colorOpts = [];
  for (const p of onShelf) {
    const pColors = (window.colors || []).filter(c => c.product_id === p.id);
    for (const c of pColors) {
      colorOpts.push({ id: c.id, label: `${p.brand} ${p.material} ${c.name}` });
    }
  }
  
  if (colorOpts.length === 0) {
    sel.innerHTML = '<option disabled selected>暂无可入库的颜色，请先在耗材页添加</option>';
  } else {
    sel.innerHTML = colorOpts.map(o => `<option value="${o.id}" ${o.id === preselectColorId ? 'selected' : ''}>${esc(o.label)}</option>`).join("");
  }
  
  document.getElementById('modal-intake-qty').value = 1;
  const submitBtn = document.getElementById('modal-intake-submit');
  
  submitBtn.onclick = async () => {
    const cId = sel.value;
    const qty = parseInt(document.getElementById('modal-intake-qty').value, 10);
    if (!cId || qty < 1) return;
    
    submitBtn.disabled = true;
    try {
      const res = await api("/api/spools", { method: "POST", body: { color_id: cId, quantity: qty } });
      const codes = res.map(r => r.short_code).join(", ");
      toast(`成功入库 ${qty} 盘！短编号: ${codes}`, "success");
      document.getElementById('modal-intake').close();
      if (location.hash === '#/spools') window.onhashchange();
      if (location.hash === '#/materials') window.onhashchange();
    } catch (ex) {
      toast(ex.message, "error");
    } finally {
      submitBtn.disabled = false;
    }
  };
  
  document.getElementById('modal-intake').showModal();
};
"""

content = content + window_funcs

with open('live_app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Injected modals and global window functions successfully.")
