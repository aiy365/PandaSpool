import io

p = 'web/live_app.js'
src = io.open(p, encoding='utf-8').read()

# R1: 入库弹窗骨架改成动态 body 容器
old_shell = '''        <div class="py-4 flex flex-col gap-4">
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
        </div>'''
new_shell = '''        <div id="modal-intake-body" class="py-4 flex flex-col gap-4">
          <p class="muted text-sm">打开时自动从拓竹云端拉取规格。</p>
        </div>'''
assert old_shell in src, 'R1 shell not found'
src = src.replace(old_shell, new_shell)

# R2: viewSpools 整体重写
start = src.index('async function viewSpools() {')
end = src.index('// ---- Global Modals Handlers ----')
NEW_SPOOLS = r'''async function viewSpools() {
  $("#page")?.classList.remove("page-wide");
  pageLoading("正在获取料盘列表...");

  let spools;
  try {
    spools = await api("/api/spools");
  } catch (ex) {
    pageError(ex);
    return;
  }

  let currentFilter = 'all';
  let currentSearch = '';

  const render = () => {
    const filtered = (spools || []).filter(s => {
      if (currentFilter !== 'all' && s.status !== currentFilter) return false;
      if (currentSearch) {
        const term = currentSearch.toLowerCase();
        const sc = (s.short_code || "").toLowerCase();
        const fn = (s.bambu_filament_name || "").toLowerCase();
        if (!sc.includes(term) && !fn.includes(term)) return false;
      }
      return true;
    });

    $("#page").innerHTML = `
      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; align-items: center;">
        <h1 class="text-2xl font-bold">物理料盘与云端同步</h1>
        <div style="display:flex; gap:.5rem;">
          <button class="btn btn-ghost" id="btn-reconcile">同步对账</button>
          <button class="btn btn-primary" id="btn-intake">快捷入库</button>
        </div>
      </div>

      <div id="reconcile-panel" class="hidden mb-4"></div>

      <div style="display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 1rem;">
        <input type="text" id="spool-search" placeholder="搜索短编号或名称..." class="input input-bordered" style="flex: 1; min-width: 200px;" value="${esc(currentSearch)}">
        <div class="tabs tabs-boxed" style="flex-wrap: nowrap; overflow-x: auto;">
          <a class="tab ${currentFilter === 'all' ? 'tab-active' : ''}" data-filter="all">全部</a>
          <a class="tab ${currentFilter === 'unopened' ? 'tab-active' : ''}" data-filter="unopened">未开封</a>
          <a class="tab ${currentFilter === 'opened' ? 'tab-active' : ''}" data-filter="opened">已开封</a>
          <a class="tab ${currentFilter === 'depleted' ? 'tab-active' : ''}" data-filter="depleted">已用完</a>
        </div>
      </div>

      <div class="overflow-x-auto shadow rounded-box bg-base-100">
        <table class="table table-zebra w-full">
          <thead>
            <tr>
              <th>短编号</th>
              <th>型号与颜色</th>
              <th>状态</th>
              <th>当前重量 (g)</th>
              <th class="hide-on-mobile">同步时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody id="spools-body">
            ${filtered.map(s => {
              const fname = s.bambu_filament_name || s.short_code;
              const hex = (s.color_hex || "").toLowerCase();
              const swatch = /^[0-9a-f]{6}$/.test(hex) ? `<span class="inline-block w-3 h-3 rounded-full border border-base-300 mr-1 align-middle" style="background:#${hex}"></span>` : "";
              const maxW = Math.max(500, Math.round(Number(s.net_weight_g) || 1000));
              return `\
              <tr>
                <td><span class="badge badge-primary font-mono">${esc(s.short_code || "N/A")}</span></td>
                <td>
                  <div class="font-bold">${swatch}${esc(fname)}</div>
                  <div class="text-xs muted hide-on-mobile">Cloud ID: ${s.bambu_cloud_id || "未绑定"}</div>
                </td>
                <td>
                  <select class="select select-bordered select-xs" data-spool="${s.id}" data-action="status">
                    <option value="unopened" ${s.status === 'unopened' ? 'selected' : ''}>未开封</option>
                    <option value="opened" ${s.status === 'opened' ? 'selected' : ''}>已开封</option>
                    <option value="depleted" ${s.status === 'depleted' ? 'selected' : ''}>已用完</option>
                  </select>
                </td>
                <td>
                  <div class="flex items-center gap-1 cursor-pointer hover:bg-base-200 p-1 rounded inline-flex" onclick="window.editWeight(\'${esc(s.id)}\', ${Number(s.net_weight_g) || 0}, ${maxW})">
                    <span class="font-mono font-bold text-primary text-lg">${s.net_weight_g}</span>
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 muted" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                  </div>
                </td>
                <td class="text-xs muted hide-on-mobile">${s.last_synced_at ? esc(s.last_synced_at.replace("T", " ").slice(0, 16)) : "从未同步"}</td>
                <td>
                  <button class="btn btn-error btn-xs btn-outline" data-spool="${s.id}" data-action="delete">报废</button>
                </td>
              </tr>
            `}).join("")}
            ${filtered.length === 0 ? `<tr><td colspan="6" class="text-center py-8 muted">还没有料盘。点「快捷入库」选拓竹云端规格建档。</td></tr>` : ""}
          </tbody>
        </table>
      </div>
    `;

    $("#spool-search")?.addEventListener("input", (e) => {
      currentSearch = e.target.value;
      render();
    });

    document.querySelectorAll(".tabs .tab").forEach(t => {
      t.addEventListener("click", (e) => {
        currentFilter = e.target.dataset.filter;
        render();
      });
    });

    $("#btn-intake")?.addEventListener("click", () => window.showIntakeModal());
    $("#btn-reconcile")?.addEventListener("click", () => window.showReconcile());

    const tbody = $("#spools-body");
    if (!tbody) return;

    tbody.addEventListener("change", async (e) => {
      if (e.target.dataset.action === "status") {
        const id = e.target.dataset.spool;
        const val = e.target.value;
        e.target.disabled = true;
        try {
          await api("/api/spools/" + id + "/status", { method: "PUT", body: { status: val } });
          toast(val === "depleted" ? "已用完，云端条目已删除" : "状态已更新", "success");
          spools.find(x => x.id === id).status = val;
        } catch (ex) {
          toast(ex.message, "error");
        } finally {
          e.target.disabled = false;
          render();
        }
      }
    });

    tbody.addEventListener("click", async (e) => {
      const btn = e.target.closest("button");
      if (!btn) return;

      if (btn.dataset.action === "delete") {
        const id = btn.dataset.spool;
        window.confirmDanger("确定要报废这个料盘吗？此操作将从本地和云端同步删除。", async () => {
          btn.disabled = true;
          try {
            await api("/api/spools/" + id, { method: "DELETE" });
            toast("已报废并删除云端记录", "success");
            spools = spools.filter(x => x.id !== id);
            render();
          } catch (ex) {
            toast(ex.message, "error");
            btn.disabled = false;
          }
        });
      }
    });
  };

  render();
}


'''
src = src[:start] + NEW_SPOOLS + src[end:]

# R3: showIntakeModal 重写 + 新增 showReconcile（替换文件尾部旧实现）
i3 = src.rindex('window.showIntakeModal')  # 取最后一处（文件尾部的旧实现），避免命中 viewSpools 里的引用
NEW_TAIL = r'''window.showIntakeModal = () => {
  const body = document.getElementById('modal-intake-body');
  const submitBtn = document.getElementById('modal-intake-submit');
  body.innerHTML = `
    <div class="form-control w-full">
      <label class="label"><span class="label-text">规格（拓竹云端耗材库的标记物）</span></label>
      <select id="intake-spec" class="select select-bordered w-full"><option>正在同步云端…</option></select>
    </div>
    <div class="form-control w-full">
      <label class="label"><span class="label-text">颜色名（要入库的实际颜色）</span></label>
      <input id="intake-color" class="input input-bordered w-full" placeholder="如：黑色 / 灰色" list="intake-color-list" autocomplete="off">
      <datalist id="intake-color-list"></datalist>
    </div>
    <div class="form-control w-full">
      <label class="label"><span class="label-text">入库盘数</span></label>
      <div class="join">
        <button class="btn join-item" type="button" onclick="document.getElementById('intake-qty').stepDown()">-</button>
        <input type="number" id="intake-qty" class="input input-bordered join-item w-full text-center" value="1" min="1" max="100">
        <button class="btn join-item" type="button" onclick="document.getElementById('intake-qty').stepUp()">+</button>
      </div>
    </div>`;
  const specSel = document.getElementById('intake-spec');
  const colorIn = document.getElementById('intake-color');
  submitBtn.disabled = true;

  api("/api/spools/cloud/sync").then(res => {
    const specs = res.specs || [];
    if (!specs.length) {
      specSel.innerHTML = '<option disabled selected>云端没有可用的规格标记物</option>';
      toast("先在拓竹云端/Studio 建一卷品牌规格（标记物），再回来点「同步对账」", "warning", { sticky: true });
      return;
    }
    specSel.innerHTML = specs.map(s => `<option value="${s.cloud_id}">${esc(s.name)}（${esc(s.filament_id)}）</option>`).join("");
    submitBtn.disabled = false;
  }).catch(ex => {
    specSel.innerHTML = `<option disabled selected>${esc(ex.message)}</option>`;
  });

  ensureCatalog().then(() => {
    const dl = document.getElementById('intake-color-list');
    if (dl) dl.innerHTML = [...new Set((window.colors || []).map(c => c.name).filter(Boolean))].map(n => `<option value="${esc(n)}">`).join("");
  });

  colorIn.oninput = () => {
    const [bg] = getDetailedColor(colorIn.value, "");
    colorIn.style.background = bg || "";
    colorIn.style.color = bg && parseInt(bg.slice(0, 2), 16) > 150 ? "#000" : (bg ? "#fff" : "");
  };

  submitBtn.onclick = async () => {
    const specId = Number(specSel.value);
    const colorName = colorIn.value.trim();
    const qty = parseInt(document.getElementById('intake-qty').value, 10);
    if (!specId || !colorName || !(qty >= 1)) { toast("选规格、填颜色名", "warning"); return; }
    const [bg] = getDetailedColor(colorName, "");
    submitBtn.disabled = true;
    try {
      const res = await api("/api/spools", { method: "POST", body: { spec_cloud_id: specId, color_name: colorName, color_hex: bg || "", quantity: qty } });
      const codes = (res.codes || []).join(", ");
      toast(`入库成功：${codes}，请用记号笔写到盘上`, "success", { sticky: true });
      document.getElementById('modal-intake').close();
      if (location.hash === '#/spools') window.onhashchange();
    } catch (ex) {
      toast(ex.message, "error");
    } finally {
      submitBtn.disabled = false;
    }
  };

  document.getElementById('modal-intake').showModal();
};

window.showReconcile = async () => {
  const panel = document.getElementById('reconcile-panel');
  if (!panel) return;
  panel.classList.remove('hidden');
  panel.innerHTML = card(`<p class="muted"><span class="loading loading-spinner loading-sm"></span> 正在与拓竹云端对账…</p>`);
  try {
    const d = await api("/api/spools/cloud/reconcile");
    const matchedRows = (d.matched || []).map(m => `<tr><td><span class="badge badge-primary font-mono">${esc(m.spool.short_code)}</span></td><td>${esc(m.spool.bambu_filament_name || "")}</td><td class="muted text-xs">${esc(m.cloud_note || "")}</td></tr>`).join("");
    const localRows = (d.local_only || []).map(s => `<tr><td><span class="badge badge-warning font-mono">${esc(s.short_code)}</span></td><td>${esc(s.bambu_filament_name || "")}</td><td><button class="btn btn-xs btn-primary" data-repair="${esc(s.id)}">补建云端</button></td></tr>`).join("");
    const cloudRows = (d.cloud_only || []).map(f => {
      const m = /([a-z]{1,3}\d{3,4})/i.exec(f.Note || "");
      return `<tr><td><span class="badge badge-error font-mono">${esc(m ? m[1] : f.ID)}</span></td><td>${esc(f.FilamentName || "")}</td><td><button class="btn btn-xs btn-error btn-outline" data-cldel="${f.ID}">清理</button></td></tr>`;
    }).join("");
    panel.innerHTML = card(`
      <div class="flex items-center justify-between flex-wrap gap-2">
        <h2 class="card-title text-base">云端对账 <span class="text-sm muted font-normal">已配对 ${(d.matched || []).length} · 本地缺云端 ${(d.local_only || []).length} · 云端孤儿 ${(d.cloud_only || []).length} · 已用完 ${d.depleted || 0}</span></h2>
        <button type="button" class="btn btn-ghost btn-xs" id="rc-close">收起</button>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-3 mt-2">
        <div><h3 class="font-semibold text-sm mb-1">✅ 两边都有</h3><div class="overflow-x-auto"><table class="table table-sm"><tbody>${matchedRows || '<tr><td class="muted text-sm">无</td></tr>'}</tbody></table></div></div>
        <div><h3 class="font-semibold text-sm mb-1">⚠️ 本地有、云端缺</h3><div class="overflow-x-auto"><table class="table table-sm"><tbody>${localRows || '<tr><td class="muted text-sm">无</td></tr>'}</tbody></table></div></div>
        <div><h3 class="font-semibold text-sm mb-1">🧹 云端孤儿（可清理）</h3><div class="overflow-x-auto"><table class="table table-sm"><tbody>${cloudRows || '<tr><td class="muted text-sm">无</td></tr>'}</tbody></table></div></div>
      </div>`);
    document.getElementById('rc-close').onclick = () => panel.classList.add('hidden');
    panel.querySelectorAll('[data-repair]').forEach(b => b.onclick = (e) => busy(e.currentTarget, async () => {
      await api("/api/spools/cloud/repair", { method: "POST", body: { spool_id: b.dataset.repair } });
      toast("云端已补建并回绑编号", "success");
      window.showReconcile();
    }, "rc"));
    panel.querySelectorAll('[data-cldel]').forEach(b => b.onclick = () => {
      window.confirmDanger("从拓竹云端删除这条孤儿条目？", async () => {
        try {
          await api("/api/spools/cloud/" + b.dataset.cldel, { method: "DELETE" });
          toast("已清理", "success");
          window.showReconcile();
        } catch (ex) { toast(ex.message, "error"); }
      });
    });
  } catch (ex) {
    panel.innerHTML = card(`<p class="text-error">${esc(ex.message)}</p>`);
  }
};
'''
src = src[:i3] + NEW_TAIL

# R4: 产品页颜色行去掉"入库"入口（入口收敛到料盘页）
old_btn = '<td class="join"><button class="btn btn-primary btn-xs join-item" data-intakec="${c.id}">入库</button><button class="btn btn-ghost btn-xs join-item" data-savec="${c.id}">存</button><button class="btn btn-ghost btn-xs join-item" data-delc="${c.id}">删</button></td>'
new_btn = '<td class="join"><button class="btn btn-ghost btn-xs join-item" data-savec="${c.id}">存</button><button class="btn btn-ghost btn-xs join-item" data-delc="${c.id}">删</button></td>'
assert old_btn in src, 'R4 button not found'
src = src.replace(old_btn, new_btn)

# R5: 删除产品页的 intakec 处理块
i5 = src.index('      if (btn.dataset.intakec) {')
j5 = src.index('      if (btn.dataset.savec) {')
src = src[:i5] + src[j5:]

io.open(p, 'w', encoding='utf-8', newline='\n').write(src)
print('frontend patched OK')
