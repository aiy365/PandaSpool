import re

with open('live_app.js', 'r', encoding='utf-8') as f:
    content = f.read()

start_idx = content.find('async function viewSpools() {')
if start_idx == -1:
    print("Could not find viewSpools")
    exit(1)

end_idx = content.find('async function viewCompare', start_idx)
if end_idx == -1:
    end_idx = len(content)

old_view_spools = content[start_idx:end_idx]

new_view_spools = """async function viewSpools() {
  $("#page")?.classList.remove("page-wide");
  pageLoading("正在获取料盘列表...");
  
  let spools;
  try {
    spools = await api("/api/spools");
  } catch (ex) {
    pageError(ex);
    return;
  }

  const getColorName = (cId) => {
    const c = window.colors?.find(x => x.id === cId);
    if (!c) return "未知规格";
    const p = window.products?.find(x => x.id === c.product_id);
    return p ? `${p.brand} ${p.material} ${c.name}` : c.name;
  };
  
  const getGrossWeight = (cId) => {
    const c = window.colors?.find(x => x.id === cId);
    if (!c) return 1000;
    const p = window.products?.find(x => x.id === c.product_id);
    return p ? (p.gross_weight_g || 1000) : 1000;
  };

  let currentFilter = 'all';
  let currentSearch = '';

  const render = () => {
    const filtered = (spools || []).filter(s => {
      if (currentFilter !== 'all' && s.status !== currentFilter) return false;
      if (currentSearch) {
        const term = currentSearch.toLowerCase();
        const sc = (s.short_code || "").toLowerCase();
        const fn = (s.bambu_filament_name || getColorName(s.color_id)).toLowerCase();
        if (!sc.includes(term) && !fn.includes(term)) return false;
      }
      return true;
    });

    $("#page").innerHTML = `
      <div class="flex flex-col md:flex-row md:items-center justify-between mb-4 gap-4">
        <h1 class="text-2xl font-bold">物理料盘与云端同步</h1>
        <button class="btn btn-primary" onclick="window.showIntakeModal()">快捷入库</button>
      </div>
      
      <div class="flex flex-col md:flex-row gap-4 mb-4">
        <input type="text" id="spool-search" placeholder="搜索短编号或名称..." class="input input-bordered w-full md:w-64" value="${currentSearch}">
        <div class="tabs tabs-boxed overflow-x-auto whitespace-nowrap">
          <a class="tab ${currentFilter === 'all' ? 'tab-active' : ''}" data-filter="all">全部</a>
          <a class="tab ${currentFilter === 'unopened' ? 'tab-active' : ''}" data-filter="unopened">未开封</a>
          <a class="tab ${currentFilter === 'opened' ? 'tab-active' : ''}" data-filter="opened">已开封</a>
          <a class="tab ${currentFilter === 'depleted' ? 'tab-active' : ''}" data-filter="depleted">已用完</a>
        </div>
      </div>
      
      <div class="overflow-x-auto shadow rounded-box bg-base-100">
        <table class="table table-zebra w-full table-sm md:table-md">
          <thead>
            <tr>
              <th>短编号</th>
              <th>型号与颜色</th>
              <th>状态</th>
              <th>当前重量 (g)</th>
              <th class="hidden md:table-cell">同步时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody id="spools-body">
            ${filtered.map(s => {
              const fname = s.bambu_filament_name || getColorName(s.color_id);
              const gw = getGrossWeight(s.color_id);
              return `\\
              <tr>
                <td><span class="badge badge-primary font-mono">${esc(s.short_code || "N/A")}</span></td>
                <td>
                  <div class="font-bold text-sm md:text-base">${esc(fname)}</div>
                  <div class="text-xs muted hidden md:block">Cloud ID: ${s.bambu_cloud_id || "未绑定"}</div>
                </td>
                <td>
                  <select class="select select-bordered select-xs" data-spool="${s.id}" data-action="status">
                    <option value="unopened" ${s.status === 'unopened' ? 'selected' : ''}>未开封</option>
                    <option value="opened" ${s.status === 'opened' ? 'selected' : ''}>已开封</option>
                    <option value="depleted" ${s.status === 'depleted' ? 'selected' : ''}>已用完</option>
                  </select>
                </td>
                <td>
                  <div class="flex items-center gap-1 cursor-pointer hover:bg-base-200 p-1 rounded inline-flex" onclick="window.editWeight('${s.id}', ${s.net_weight_g}, ${gw})">
                    <span class="font-mono font-bold text-primary text-lg">${s.net_weight_g}</span>
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 muted" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                  </div>
                </td>
                <td class="text-xs muted hidden md:table-cell">${s.last_synced_at ? esc(s.last_synced_at.replace("T", " ").slice(0, 16)) : "从未同步"}</td>
                <td>
                  <button class="btn btn-error btn-xs btn-outline" data-spool="${s.id}" data-action="delete">报废</button>
                </td>
              </tr>
            `}).join("")}
            ${filtered.length === 0 ? `<tr><td colspan="6" class="text-center py-8 muted">没有找到匹配的料盘</td></tr>` : ""}
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

    const tbody = $("#spools-body");
    if (!tbody) return;

    tbody.addEventListener("change", async (e) => {
      if (e.target.dataset.action === "status") {
        const id = e.target.dataset.spool;
        const val = e.target.value;
        e.target.disabled = true;
        try {
          await api("/api/spools/" + id + "/status", { method: "PUT", body: { status: val } });
          toast("状态已更新并同步云端", "success");
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
"""

content = content.replace(old_view_spools, new_view_spools)

with open('live_app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Replaced viewSpools successfully.")
