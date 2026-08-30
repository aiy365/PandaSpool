const $ = (s, el = document) => el.querySelector(s);
const root = $("#root");

const THEME_KEY = "pp-theme";
function currentTheme() { return localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light"; }
function applyTheme(theme) {
  const t = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = t;
  document.documentElement.style.colorScheme = t;
  const meta = document.querySelector('meta[name="color-scheme"]');
  if (meta) meta.content = t;
  localStorage.setItem(THEME_KEY, t);
  document.querySelectorAll("[data-theme-toggle]").forEach((b) => {
    b.innerHTML = t === 'dark' ? `<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='5'/><path d='M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42'/></svg>` : `<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'></path></svg>`;
    b.setAttribute("aria-label", t === "dark" ? "切换到浅色" : "切换到深色");
  });
}
function toggleTheme() { applyTheme(currentTheme() === "dark" ? "light" : "dark"); }
function themeBtn() { return `<button type="button" class="btn btn-ghost btn-sm" data-theme-toggle></button>`; }
document.addEventListener("click", (e) => { if (e.target.closest("[data-theme-toggle]")) toggleTheme(); });
applyTheme(currentTheme());


function updateAppTitle(title) {
  const displayTitle = title || "PandaSpool";
  document.title = displayTitle;
  const brandEl = document.getElementById("brand");
  if (brandEl) brandEl.innerText = displayTitle;
}
async function api(path, opts = {}) {
  const res = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
    body: opts.body && typeof opts.body !== "string" ? JSON.stringify(opts.body) : opts.body,
  });
  const txt = await res.text();
  let data = {};
  try { data = txt ? JSON.parse(txt) : {}; } catch { data = { error: txt }; }
  if (!res.ok) throw new Error(data.error || txt || res.statusText);
  return data;
}

function h(html) { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content; }
function val(form, name) { return form.elements[name]?.value ?? ""; }
function route() { return location.hash.replace(/^#/, "") || "/"; }
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

// 产品/颜色目录缓存：料盘页的入库弹窗和机台页的料盘匹配都依赖它。
async function ensureCatalog(force = false) {
  if (!force && window.products && window.colors && Date.now() < (window.__catExp || 0)) return;
  try {
    const [ps, cs] = await Promise.all([api("/api/products"), api("/api/colors")]);
    window.products = ps || [];
    window.colors = cs || [];
    window.__catExp = Date.now() + 60 * 1000;
  } catch { /* 目录失败不阻塞主数据渲染 */ }
}

function toastHost() {
  let host = $("#pp-toast");
  if (host) return host;
  host = document.createElement("div");
  host.id = "pp-toast";
  host.className = "pp-toast-host";
  host.setAttribute("aria-live", "polite");
  host.setAttribute("aria-relevant", "additions");
  document.body.appendChild(host);
  return host;
}

function toast(text, kind = "info", opts = {}) {
  const host = toastHost();
  if (opts.id) host.querySelector(`[data-toast="${opts.id}"]`)?.remove();
  while (host.children.length >= 3) host.firstElementChild.remove();
  const el = document.createElement("div");
  const cls = { error: "alert-error", success: "alert-success", warning: "alert-warning", info: "alert-info" }[kind] || "alert-info";
  el.className = `alert ${cls} shadow-lg pp-toast`;
  if (opts.id) el.dataset.toast = opts.id;
  if (kind === "error") el.setAttribute("role", "alert");
  const spin = opts.sticky ? `<span class="loading loading-spinner loading-xs"></span>` : "";
  el.innerHTML = `${spin}<span>${esc(String(text ?? ""))}</span><button type="button" class="btn btn-ghost btn-xs btn-circle" aria-label="关闭">×</button>`;
  el.querySelector("button").onclick = () => el.remove();
  host.appendChild(el);
  if (!opts.sticky && kind !== "error") {
    setTimeout(() => { if (el.isConnected) el.remove(); }, kind === "success" ? 3200 : 4500);
  }
  return el;
}

document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const host = $("#pp-toast");
  const last = host?.lastElementChild;
  if (last) last.remove();
});

async function busy(btn, fn, id) {
  if (btn?.dataset.busy) return;
  const html = btn ? btn.innerHTML : "";
  if (btn) {
    btn.dataset.busy = "1";
    btn.classList.add("btn-disabled");
    btn.setAttribute("aria-busy", "true");
    btn.innerHTML = `<span class="loading loading-spinner loading-xs"></span> ${esc(btn.textContent.trim())}`;
  }
  try {
    await fn();
  } catch (ex) {
    toast(ex.message || String(ex), "error", { id });
  } finally {
    if (btn) {
      delete btn.dataset.busy;
      btn.classList.remove("btn-disabled");
      btn.removeAttribute("aria-busy");
      btn.innerHTML = html;
    }
  }
}

function pageError(ex) {
  const msg = ex?.message || String(ex);
  toast(msg, "error");
  if ($("#page")) $("#page").innerHTML = card(`<p class="text-error">${esc(msg)}</p>`);
}

function pageLoading(text) {
  if ($("#page")) $("#page").innerHTML = card(`<p class="muted"><span class="loading loading-spinner loading-sm"></span> ${esc(text || "加载中…")}</p>`);
}

function describeStatus(st) {
  if (st == null) return { t: "完成", k: "success" };
  if (typeof st === "string") return { t: st, k: "info" };
  if (st.error) return { t: String(st.error), k: "error" };
  if (st.hint) return { t: String(st.hint), k: "success" };
  if (st.connected) return { t: "拓竹 MQTT 已连接", k: "success" };
  if (st.need_code) return { t: "需要验证码，先点发送", k: "warning" };
  if (st.ok && st.token_len) return { t: `萤石可用（token ${st.token_len}）`, k: "success" };
  if (st.ok && Array.isArray(st.devices)) return { t: `已登录，拉到 ${st.devices.length} 台设备`, k: "success" };
  if (st.ok) return { t: "完成", k: "success" };
  if (st.has_token) return { t: "已有 token，MQTT 尚未连上", k: "warning" };
  return { t: "未连接", k: "warning" };
}

function field(label, control) {
  return `<label class="form-control w-full">
    <div class="label py-1"><span class="label-text">${esc(label)}</span></div>
    ${control}
  </label>`;
}
function inputEl(id, extra = "") {
  return `<input id="${id}" class="input input-bordered w-full" ${extra}>`;
}
function selectEl(id, options, extra = "") {
  return `<select id="${id}" class="select select-bordered w-full" ${extra}>${options}</select>`;
}
function textareaEl(id, value = "", extra = "") {
  return `<textarea id="${id}" class="textarea textarea-bordered w-full" ${extra}>${esc(value)}</textarea>`;
}
function card(inner) {
  return `<section class="card bg-base-100 shadow-sm border border-base-300 masonry-item">${inner.includes("card-body") ? inner : `<div class="card-body p-4 sm:p-6">${inner}</div>`}</section>`;
}
function joinOnOff(idAttr, idVal, onKey = "on") {
  return `<span class="join">
    <button type="button" class="btn btn-sm join-item btn-primary" ${idAttr}="${esc(idVal)}" data-${onKey}="1">开</button>
    <button type="button" class="btn btn-sm join-item btn-ghost" ${idAttr}="${esc(idVal)}" data-${onKey}="0">关</button>
  </span>`;
}

function bindRow(label, inputId, id) {
  const has = id ? `<code class="text-xs">${esc(id)}</code>
    <span class="join">
      <button type="button" class="btn btn-xs join-item btn-primary" data-sw="${esc(id)}" data-on="1">试开</button>
      <button type="button" class="btn btn-xs join-item btn-ghost" data-sw="${esc(id)}" data-on="0">试关</button>
    </span>` : `<span class="muted">还没绑</span>`;
  return `<div class="sw"><span>${esc(label)}</span><span class="bindbar">
    <input type="hidden" id="${inputId}" value="${esc(id || "")}">${has}
  </span></div>`;
}

async function boot() {
  const b = await api("/api/bootstrap");
  if (b.needs_setup) return renderSetup();
  try {
    const me = await api("/api/me");
    renderApp(me);
  } catch {
    renderLogin();
  }
}

function renderSetup() {
  root.innerHTML = "";
  root.append(h(`<div class="auth min-h-screen bg-base-200"><div class="auth-tools">${themeBtn()}</div>
    ${card(`
      <h1 class="card-title">初始化这台 PandaSpool</h1>
      <p class="muted">用户名密码只存在本机数据目录，之后在设置页改。拷给第二个人也是先走这一步。</p>
      <form id="f" class="flex flex-col gap-2">
        ${field("站点名称", `<input name="title" class="input input-bordered w-full" value="PandaSpool">`)}
        ${field("管理员", `<input name="username" class="input input-bordered w-full" value="admin">`)}
        ${field("密码（≥6 位）", `<input name="password" type="password" class="input input-bordered w-full">`)}
        <p class="text-error" id="err"></p>
        <div class="card-actions"><button class="btn btn-primary" type="submit">开始使用</button></div>
      </form>
    `)}
  </div>`));
  $("#f").onsubmit = async (e) => {
    e.preventDefault();
    try {
      await api("/api/setup", { method: "POST", body: { title: val($("#f"), "title"), username: val($("#f"), "username"), password: val($("#f"), "password") } });
      location.reload();
    } catch (ex) { $("#err").textContent = ex.message; }
  };
  applyTheme(currentTheme());
}

function renderLogin() {
  root.innerHTML = "";
  root.append(h(`<div class="auth min-h-screen bg-base-200"><div class="auth-tools">${themeBtn()}</div>
    ${card(`
      <h1 class="card-title">登录</h1>
      <form id="f" class="flex flex-col gap-2">
        ${field("用户名", `<input name="username" class="input input-bordered w-full">`)}
        ${field("密码", `<input name="password" type="password" class="input input-bordered w-full">`)}
        <p class="text-error" id="err"></p>
        <div class="card-actions"><button class="btn btn-primary" type="submit">进入</button></div>
      </form>
    `)}
  </div>`));
  $("#f").onsubmit = async (e) => {
    e.preventDefault();
    try {
      await api("/api/login", { method: "POST", body: { username: val($("#f"), "username"), password: val($("#f"), "password") } });
      boot();
    } catch (ex) { $("#err").textContent = ex.message; }
  };
  applyTheme(currentTheme());
}

function renderApp(me) {
  root.innerHTML = "";
  root.append(h(`<div class="shell bg-base-200">
    <header class="topbar">
      <!-- Mobile Nav -->
      <div class="dropdown nav-mobile">
        <div tabindex="0" role="button" class="btn btn-ghost">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16" /></svg>
        </div>
        <ul tabindex="0" class="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52">
          <li><a href="#/" data-p="/">总览</a></li>
          <li><a href="#/materials" data-p="/materials">耗材</a></li>
          <li><a href="#/spools" data-p="/spools">料盘</a></li>
          <li><a href="#/stock" data-p="/stock">盘点</a></li>
          <li><a href="#/compare" data-p="/compare">横评</a></li>
          <li><a href="#/machine" data-p="/machine">机台</a></li>
          <li><a href="#/air" data-p="/air">空气</a></li>
          <li><a href="#/settings" data-p="/settings">设置</a></li>
        </ul>
      </div>
      
      <span class="btn btn-ghost text-lg text-primary" id="brand">${esc(me.title || "PandaSpool")}</span>
      
      <!-- Desktop Nav -->
      <nav class="menu menu-horizontal px-1 nav-desktop">
        <li><a href="#/" data-p="/">总览</a></li>
        <li><a href="#/materials" data-p="/materials">耗材</a></li>
        <li><a href="#/spools" data-p="/spools">料盘</a></li>
        <li><a href="#/stock" data-p="/stock">盘点</a></li>
        <li><a href="#/compare" data-p="/compare">横评</a></li>
        <li><a href="#/machine" data-p="/machine">机台</a></li>
        <li><a href="#/air" data-p="/air">空气</a></li>
        <li><a href="#/settings" data-p="/settings">设置</a></li>
      </nav>
      
      <div class="grow"></div>
      ${themeBtn()}
      <button class="btn btn-ghost btn-sm" id="out">退出</button>
    </header>
    
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
        <div id="modal-intake-body" class="py-4 flex flex-col gap-4">
          <p class="muted text-sm">打开时自动从拓竹云端拉取规格。</p>
        </div>
        <div class="modal-action">
          <form method="dialog"><button class="btn">取消</button></form>
          <button class="btn btn-primary" id="modal-intake-submit">确认入库</button>
        </div>
      </div>
    </dialog>

  </div>`));
  $("#out").onclick = async () => { await api("/api/logout", { method: "POST", body: {} }); boot(); };
  window.onhashchange = () => paint(me);
  applyTheme(currentTheme());
  paint(me);
}

function stopMachineLive() {
  if (window.__machTimer) {
    clearInterval(window.__machTimer);
    window.__machTimer = null;
  }
  if (window.__ez) {
    try { window.__ez.stop?.(); } catch { /* kit 版本不一 */ }
    try { window.__ez.destroy?.(); } catch { /* ignore */ }
    window.__ez = null;
  }
}

function airAgeText(ts) {
  let n = Number(ts);
  if (!n) return "";
  if (n > 1e12) n = Math.round(n / 1000);
  const age = Math.round(Date.now() / 1000) - n;
  if (age < 0) return "";
  if (age < 90) return "刚刚";
  if (age < 3600) return `${Math.round(age / 60)} 分钟前`;
  if (age < 86400) return `${Math.round(age / 3600)} 小时前`;
  return `${Math.round(age / 86400)} 天前`;
}

function resolveColorRef(p, raw) {
  const t = String(raw || "").trim();
  if (!t) return "";
  const colors = p.colors || [];
  if (colors.some((c) => c.id === t)) return t;
  const hits = colors.filter((c) => c.name === t);
  if (hits.length === 1) return hits[0].id;
  return t;
}

function paint(me) {
  document.querySelectorAll(".menu a").forEach((a) => {
    const on = route().startsWith(a.dataset.p) && (a.dataset.p !== "/" || route() === "/");
    a.classList.toggle("menu-active", on);
    a.classList.toggle("active", on);
  });
  $("#page")?.classList.remove("page-wide");
  const p = route();
  if (p !== "/machine") stopMachineLive();
  const run = () => {
    if (p === "/") return viewHome();
    if (p === "/materials") return viewMaterials();
    if (p.startsWith("/materials/")) return viewProduct(p.split("/")[2]);
    if (p === "/spools") return viewSpools();
    if (p === "/stock") return viewStock();
    if (p === "/compare") return viewCompare();
    if (p === "/machine") return viewMachine();
    if (p === "/air") return viewAir();
    if (p === "/settings") return viewSettings(me);
    return viewHome();
  };
  Promise.resolve(run()).catch(pageError);
}

async function viewHome() {
  pageLoading("正在加载总览…");
  let d;
  try { d = await api("/api/summary"); }
  catch (ex) { pageError(ex); return; }
  const m = d.machine || {};
  const air = d.air || {};
  const mqtt = m.error && !m.connected
    ? `<span class="badge badge-error badge-outline">${esc(m.error)}</span>`
    : m.connected
      ? `<span class="badge badge-success">MQTT 已连接</span>`
      : `<a href="#/settings" class="badge badge-ghost hover:badge-primary cursor-pointer">未连接拓竹，点击去设置页填写</a>`;

  const printing = !!d.printing;
  const job = m.subtask || m.job || "";
  const remain = m.remaining != null && m.remaining !== "" ? m.remaining : "—";
  const boost = m.print_boost_active ? `<span class="badge badge-warning">打印加强开着</span>` : "";
  const airAge = airAgeText(air.ts);
  let airTs = Number(air.ts);
  if (airTs > 1e12) airTs /= 1000;
  const airStale = airTs ? (Date.now() / 1000 - airTs) > 15 * 60 : false;
  const todo = [];
  if ((d.drafts || 0) > 0) todo.push(`草稿 ${d.drafts} 条待确认`);
  if ((d.inbox || 0) > 0) todo.push(`收集箱 ${d.inbox} 张待处理`);
  $("#page").innerHTML = `
    <div class="stats stats-vertical lg:stats-horizontal shadow-sm bg-base-100 border border-base-300 mb-4">
      <div class="stat"><div class="stat-title">产品</div><div class="stat-value text-primary">${d.products}</div></div>
      <div class="stat"><div class="stat-title">颜色</div><div class="stat-value">${d.colors}</div></div>
      <div class="stat"><div class="stat-title">未开封 / 开封</div><div class="stat-value">${d.unopened} / ${d.opened}</div></div>
      <div class="stat"><div class="stat-title">草稿 / 待处理图</div><div class="stat-value">${d.drafts ?? 0} / ${d.inbox ?? 0}</div></div>
    </div>
    <div class="masonry-grid">
    ${card(`
      <h2 class="card-title">机台</h2>
      <p class="mb-2">${mqtt} ${m.connected ? (printing ? `<span class="badge badge-success">打印中 ${m.progress ?? "—"}%</span>` : `<span class="badge badge-ghost">${esc(m.gcode_state || m.stage || "空闲")}</span>`) : ""} ${boost}</p>
      ${m.connected ? `
        <p>${printing ? `${esc(job || "正在打印")}　剩余 ${esc(remain)} 分钟` : `热床 ${m.bed_temp ?? "—"}°C　喷嘴 ${m.nozzle_temp ?? "—"}°C`}</p>
        <p class="muted">${printing ? `热床 ${m.bed_temp ?? "—"}°C　喷嘴 ${m.nozzle_temp ?? "—"}°C　层 ${m.layer ?? "—"}/${m.total_layer ?? "—"}` : esc(job)}</p>
      ` : `
        <div class="py-2 text-center text-sm muted bg-base-200 rounded-box my-2">机器未连接，无法读取温度或任务状态。</div>
      `}
      <div class="card-actions mt-2"><a class="btn btn-sm btn-primary" href="#/machine">打开机台页</a></div>
    `)}
    ${card(`
      <h2 class="card-title">空气</h2>
      ${air.ts ? `
        <p>PM2.5 <strong>${air.pm25 ?? "—"}</strong> µg/m³　室温 ${air.t_c ?? "—"} ℃　湿度 ${air.rh ?? "—"} %</p>
        <p class="${airStale ? "text-warning" : "muted"} mt-2">探头 ${esc(airAge || "")}${airStale ? " · 超过 15 分钟没报" : ""}　有人 ${air.presence ?? "—"}</p>
      ` : `
        <div class="py-2 text-center text-sm muted bg-base-200 rounded-box my-2">尚未接入环境探头，无空气数据。</div>
      `}
      <div class="card-actions mt-2"><a class="btn btn-sm btn-ghost" href="#/air">空气记录</a><a class="btn btn-sm btn-ghost" href="#/stock">架子盘点</a></div>
    `)}
    </div>
    ${todo.length ? card(`<h2 class="card-title">待办</h2><p>${esc(todo.join(" · "))}</p><p class="muted">去对应产品页确认草稿、处理收集箱。AI 不会自动覆盖已确认条目。</p>`) : ""}
  `;
}

function colorOnShelf(c) {
  return Number(c.unopened || 0) > 0 || Number(c.opened || 0) > 0;
}

function productStock(p) {
  const all = p.colors || [];
  const shelf = all.filter(colorOnShelf);
  return {
    all,
    shelf,
    unopened: shelf.reduce((n, c) => n + Number(c.unopened || 0), 0),
    opened: shelf.filter((c) => Number(c.opened || 0) > 0).length,
    catalog: all.length,
  };
}

function specStrip(card) {
  if (!card) return "";
  const order = ["烘干", "喷嘴", "热床", "速度"];
  const bits = order.filter((k) => card[k]).map((k) => `<span><em>${esc(k)}</em>${esc(card[k])}</span>`);
  if (!bits.length) return "";
  return `<div class="inv-specs">${bits.join("")}</div>`;
}

function yuan(n) {
  const x = Number(n);
  if (!x) return "—";
  return "¥" + x.toFixed(1);
}

function productCost(p) {
  let qty = 0, cost = 0;
  for (const c of p.colors || []) {
    const q = Number(c.buy_qty || 0);
    if (q > 0) {
      qty += q;
      cost += Number(c.avg_price || 0) * q;
    }
  }
  return { qty, cost, avg: qty ? cost / qty : 0 };
}

function getDetailedColor(name, fam) {
  const n = name || "";
  if (n.includes("黑")) return ["#171717", false];
  if (n.includes("深灰") || n.includes("钢铁灰")) return ["#52525b", false];
  if (n.includes("浅灰") || n.includes("银")) return ["#d4d4d8", true];
  if (n.includes("灰")) return ["#71717a", false];
  if (n.includes("白")) return ["#ffffff", true];
  if (n.includes("粉")) return ["#f472b6", true];
  if (n.includes("酒红") || n.includes("深红")) return ["#be123c", false];
  if (n.includes("洋红") || n.includes("玫红")) return ["#d946ef", false];
  if (n.includes("红")) return ["#ef4444", false];
  if (n.includes("橙")) return ["#f97316", true];
  if (n.includes("黄") || n.includes("金")) return ["#eab308", true];
  if (n.includes("深绿") || n.includes("墨绿")) return ["#166534", false];
  if (n.includes("浅绿") || n.includes("嫩绿")) return ["#86efac", true];
  if (n.includes("绿")) return ["#22c55e", false];
  if (n.includes("青")) return ["#06b6d4", true];
  if (n.includes("天蓝") || n.includes("浅蓝") || n.includes("冰川")) return ["#38bdf8", true];
  if (n.includes("深蓝") || n.includes("电光蓝")) return ["#1d4ed8", false];
  if (n.includes("蓝")) return ["#3b82f6", false];
  if (n.includes("深紫")) return ["#581c87", false];
  if (n.includes("紫")) return ["#a855f7", false];
  if (n.includes("棕") || n.includes("木")) return ["#78350f", false];
  if (n.includes("骨") || n.includes("米") || n.includes("肤")) return ["#fef3c7", true];
  if (n.includes("透明") || n.includes("自然")) return ["#e0f2fe", true];
  return [FAMILY_COLOR[fam] || "", LIGHT_FAM.has(fam)];
}

function stockChip(c) {
  const u = Number(c.unopened || 0);
  const o = Number(c.opened || 0) > 0;
  const fam = c.color_family || "";
  const [bg, isLight] = getDetailedColor(c.name, fam);
  const fg = isLight ? "#000" : "#fff";
  const style = bg ? `style="background:${bg}; color:${fg};"` : "";
  return `<span class="stock-chip ${o ? "is-open" : "is-sealed"}" title="${esc(fam)}" ${style}>
    <span class="stock-name">${esc(c.name)}</span>
    <span class="stock-qty" ${bg ? `style="color:var(--color-base-content)"` : ""}>${u}</span>
    ${o ? `<span class="badge badge-warning badge-xs">开封</span>` : ""}
  </span>`;
}

const {
  FAMILY_ORDER, BUCKET_ORDER, SLICE_ORDER, FAMILY_COLOR, LIGHT_FAMS,
  materialBucket, sliceKind, familyOf, heatLevel, buildStockMatrix,
} = globalThis.PPStock;
const LIGHT_FAM = new Set(LIGHT_FAMS);

function jumpStock(spec) {
  sessionStorage.setItem("pp-stock-jump", JSON.stringify(spec));
  location.hash = "#/materials";
}

function openNote(n) {
  return n ? ` ${n}开` : "";
}

function familyStackBar(label, n, max, famCounts) {
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
    <span class="stk-track">${n ? `<span class="stk-stack" style="width:${pct}%">${segs}</span>` : ""}</span>
    <b>${n}</b>
  </button>`;
}

function cellSplitHTML(fam, bucket, slices) {
  const order = SLICE_ORDER[bucket] || [];
  const parts = order.map((name) => {
    const s = slices?.[name];
    if (!s || !s.n) return null;
    return { name, n: s.n, opened: s.opened };
  }).filter(Boolean);
  if (parts.length < 2) return "";
  return `<div class="stk-split">${parts.map((p) =>
    `<button type="button" class="stk-slice" style="flex:${p.n}" data-fam="${esc(fam)}" data-bkt="${esc(bucket)}" data-slice="${esc(p.name)}"><strong>${p.n}${openNote(p.opened)}</strong><em>${esc(p.name)}</em></button>`
  ).join("")}</div>`;
}

async function viewStock() {
  $("#page").classList.add("page-wide");
  pageLoading("正在汇总架子…");
  let list;
  try { list = await api("/api/products"); }
  catch (ex) { pageError(ex); return; }
  const m = buildStockMatrix(list);
  let buyQty = 0, buyCost = 0;
  for (const p of list || []) {
    const pc = productCost(p);
    buyQty += pc.qty;
    buyCost += pc.cost;
  }
  const buyAvg = buyQty ? buyCost / buyQty : 0;
  const maxFam = Math.max(1, ...m.fams.map((f) => m.rowSum[f] || 0));
  const maxBkt = Math.max(1, ...m.buckets.map((b) => m.colSum[b] || 0));
  const bar = (label, n, max, color, fam) => {
    const pct = Math.max(n ? 8 : 0, Math.round((n / max) * 100));
    const light = LIGHT_FAM.has(fam) ? " is-light" : "";
    return `<button type="button" class="stk-bar stk-bar-btn" data-fam="${esc(fam)}" title="只看 ${esc(label)}">
      <span class="stk-bar-lab">${esc(label)}</span>
      <span class="stk-track"><span class="stk-fill${light}" style="width:${pct}%;background:${color}"></span></span>
      <b>${n}</b>
    </button>`;
  };
  const cellOf = (f, b) => m.cells.get(f + "\0" + b) || { n: 0, opened: 0, bits: [], slices: {} };
  const gapList = m.gaps.slice(0, 12).map((g) =>
    `<li><button type="button" class="stk-link" data-fam="${esc(g.f)}" data-bkt="${esc(g.b)}" data-empty="1">${esc(g.f)} × ${esc(g.b)}</button></li>`
  ).join("") || `<li class="muted">色系和材料对得上，没有明显空档。</li>`;
  const extraList = m.extra.filter((x) => x.n >= 5).slice(0, 8).map((g) =>
    `<li><button type="button" class="stk-link" data-fam="${esc(g.f)}" data-bkt="${esc(g.b)}">${esc(g.f)} × ${esc(g.b)} <b>${g.n}</b></button></li>`
  ).join("") || `<li class="muted">没有 ≥5 盘的格子，分布还算散。</li>`;
  const singleLine = m.singles.length
    ? m.singles.map((f) => `<button type="button" class="stk-link" data-fam="${esc(f)}">${esc(f)}</button>`).join("、")
    : "没有独苗色系。";

  $("#page").innerHTML = `
    ${card(`
      <h1 class="card-title mb-1">架子分布</h1>
      <p class="muted text-sm">盘数 = 未开封 + 开封（开封算 1 盘）。格子先只显示总数，悬停才按普通 / 哑光切开。点切开的一块只跳那一类。</p>
      <div class="stats stats-vertical lg:stats-horizontal shadow-sm bg-base-200 mt-3">
        <div class="stat py-3"><div class="stat-title">架子总盘</div><div class="stat-value text-primary text-3xl">${m.total}</div></div>
        <div class="stat py-3"><div class="stat-title">PLA 族</div><div class="stat-value text-3xl">${m.pla}</div><div class="stat-desc">含哑光 / Lite，丝绸单列</div></div>
        <div class="stat py-3"><div class="stat-title">PETG 族</div><div class="stat-value text-3xl">${m.petg}</div><div class="stat-desc">含 HF，哑光单列</div></div>
        <div class="stat py-3"><div class="stat-title">哑光</div><div class="stat-value text-3xl">${m.matte}</div><div class="stat-desc">PLA 格内哑光 + PETG 哑光</div></div>
        <div class="stat py-3"><div class="stat-title">入库均价</div><div class="stat-value text-3xl">${buyAvg ? yuan(buyAvg) : "—"}</div><div class="stat-desc">${buyQty ? `已记 ${buyQty} 盘` : "还没有入库单价"}</div></div>
      </div>
    `)}
    ${card(`
      <h2 class="card-title text-base">色系 × 材料</h2>
      <div class="stk-wrap">
        <table class="stk-table">
          <thead><tr>
            <th></th>
            ${m.buckets.map((b) => `<th>${esc(b)}<div class="stk-colsum">${m.colSum[b] || 0}</div></th>`).join("")}
            <th>合计</th>
          </tr></thead>
          <tbody>
            ${m.fams.map((f) => `<tr>
              <th class="stk-rowhead"><i class="stk-dot" style="background:${FAMILY_COLOR[f] || "#94a3b8"}"></i>${esc(f)}</th>
              ${m.buckets.map((b) => {
                const cell = cellOf(f, b);
                const lv = heatLevel(cell.n);
                const open = cell.opened ? `<small>${cell.opened}开</small>` : "";
                const split = cell.n ? cellSplitHTML(f, b, cell.slices) : "";
                const cls = split ? " stk-has-split" : "";
                const tip = split ? "" : (cell.bits.length
                  ? cell.bits.map((x) => `${x.label} · ${x.color} ${x.n}盘${x.slice ? " · " + x.slice : ""}`).join("\n")
                  : `${f} × ${b}：架子上没有`);
                return `<td class="stk-cell stk-lv${lv}${cls}" data-fam="${esc(f)}" data-bkt="${esc(b)}"${tip ? ` title="${esc(tip)}"` : ""}">${cell.n ? `<div class="stk-sum"><b>${cell.n}</b>${open}</div>${split}` : `<span class="stk-zero">—</span>`}</td>`;
              }).join("")}
              <td class="stk-total"><b>${m.rowSum[f] || 0}</b></td>
            </tr>`).join("")}
            <tr class="stk-foot">
              <th>合计</th>
              ${m.buckets.map((b) => `<td><b>${m.colSum[b] || 0}</b></td>`).join("")}
              <td><b>${m.total}</b></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="muted text-sm mt-2">有切开的格子：鼠标悬停（手机点一下）才分成普通 / Lite / 哑光，或 PETG 的普通 / HF。</p>
    `)}
    <div class="row cols-2">
      ${card(`<h2 class="card-title text-base">按色系</h2>${m.fams.map((f) => bar(f, m.rowSum[f] || 0, maxFam, FAMILY_COLOR[f] || "#94a3b8", f)).join("")}`)}
      ${card(`<h2 class="card-title text-base">按材料</h2>${m.buckets.map((b) => familyStackBar(b, m.colSum[b] || 0, maxBkt, m.famByBucket[b] || {})).join("")}`)}
    </div>
    <div class="stk-bottom">
      ${card(`<p class="text-sm">独苗色系（整架只 1 盘）：${singleLine}</p>`)}
      <div class="row cols-2 stk-insights">
        ${card(`<h2 class="card-title text-base">缺口</h2><p class="muted text-sm mb-1">有色系、有材料、格子却是空的</p><ul class="stk-list">${gapList}</ul>`)}
        ${card(`<h2 class="card-title text-base">偏多</h2><p class="muted text-sm mb-1">单格 ≥ 5 盘，可能可以少囤</p><ul class="stk-list">${extraList}</ul>`)}
      </div>
    </div>
  `;

  $("#page").onclick = (e) => {
    const sliceBtn = e.target.closest("[data-slice]");
    const cell = e.target.closest(".stk-cell");
    const coarse = window.matchMedia("(hover: none)").matches;
    if (cell?.classList.contains("stk-has-split") && coarse && !sliceBtn && !cell.classList.contains("is-split")) {
      document.querySelectorAll(".stk-cell.is-split").forEach((c) => c.classList.remove("is-split"));
      cell.classList.add("is-split");
      return;
    }
    const btn = e.target.closest("[data-fam]");
    if (!btn) {
      document.querySelectorAll(".stk-cell.is-split").forEach((c) => c.classList.remove("is-split"));
      return;
    }
    const fam = btn.dataset.fam;
    const bkt = btn.dataset.bkt || "";
    const slice = sliceBtn?.dataset.slice || "";
    const empty = btn.dataset.empty === "1" || (cell && heatLevel(cellOf(fam, bkt).n) === 0);
    jumpStock({ family: fam, bucket: bkt, slice, filter: empty ? "all" : "shelf" });
  };
}

async function viewMaterials() {
  $("#page").classList.add("page-wide");
  pageLoading("正在加载耗材…");
  let list;
  try { list = await api("/api/products"); }
  catch (ex) { pageError(ex); return; }
  $("#page").classList.add("page-wide");
  const brands = [...new Set((list || []).map((p) => p.brand).filter(Boolean))];
  let jump = {};
  try { jump = JSON.parse(sessionStorage.getItem("pp-stock-jump") || "{}"); } catch { jump = {}; }
  sessionStorage.removeItem("pp-stock-jump");
  $("#page").innerHTML = `
    ${card(`
      <div class="inv-head">
        <div>
          <h1 class="card-title mb-1">耗材盘点</h1>
          <p class="muted text-sm">默认只看架子上的卷。色卡目录收在「色卡 n 色」，点进产品再改库存。</p>
        </div>
        <details class="inv-new" id="inv-new-details">
            <summary class="btn btn-outline btn-sm">新建产品</summary>
            <div class="inv-new-body">
              <div class="row cols-2">
                ${field("关联官方预设", selectEl("new_bpi", `<option value="">-- 请先抓取并选择底层预设 --</option>`))}
                ${field("细分系列", inputEl("l", `placeholder="如：哑光 / 渐变 (选填)"`))}
              </div>
              <div class="row cols-2">
                ${field("品牌 (自动锁定)", inputEl("b", `readonly class="input input-bordered w-full bg-base-200"`))}
                ${field("材质 (自动锁定)", inputEl("m", `readonly class="input input-bordered w-full bg-base-200"`))}
              </div>
              <div class="card-actions"><button class="btn btn-primary btn-sm" id="add">创建并进入</button></div>
          </div>
        </details>
      </div>
      <div class="inv-toolbar">
        <input id="invq" class="input input-bordered input-sm inv-search" placeholder="搜品牌 / 系列 / 材料 / 颜色">
        <select id="invbrand" class="select select-bordered select-sm">
          <option value="">全部品牌</option>
          ${brands.map((b) => `<option value="${esc(b)}">${esc(b)}</option>`).join("")}
        </select>
        <div class="join">
          <button type="button" class="btn btn-sm join-item" data-invf="shelf">架子上</button>
          <button type="button" class="btn btn-sm join-item" data-invf="all">全部产品</button>
        </div>
      </div>
    `)}
    <div id="invjump"></div>
    <div id="invsum" class="inv-sum muted text-sm"></div>
    <div id="list" class="inv-list"></div>`;

  let filter = jump.filter || sessionStorage.getItem("pp-inv-filter") || "shelf";
  let query = jump.q || "";
  let brand = "";
  const jumpFam = jump.family || "";
  const jumpBkt = jump.bucket || "";
  const jumpSlice = jump.slice || "";
  if (query) $("#invq").value = query;
  if (jumpFam || jumpBkt || jumpSlice) {
    const chips = [jumpFam, jumpBkt, jumpSlice].filter(Boolean).map((x) => `<span class="badge badge-ghost">${esc(x)}</span>`).join(" ");
    $("#invjump").innerHTML = `<p class="stk-jump muted text-sm">从盘点跳来 ${chips}　<button type="button" class="btn btn-ghost btn-xs" id="invjumpx">清除筛选</button></p>`;
    $("#invjumpx").onclick = () => { sessionStorage.removeItem("pp-stock-jump"); viewMaterials(); };
  }

  const render = () => {
    document.querySelectorAll("[data-invf]").forEach((b) => {
      b.classList.toggle("btn-primary", b.dataset.invf === filter);
      b.classList.toggle("btn-ghost", b.dataset.invf !== filter);
    });
    const q = query.trim().toLowerCase();
    const rows = (list || []).map((p) => ({ p, s: productStock(p) })).filter(({ p, s }) => {
      if (filter === "shelf" && s.shelf.length === 0) return false;
      if (brand && p.brand !== brand) return false;
      if (jumpBkt && materialBucket(p) !== jumpBkt) return false;
      if (jumpSlice && sliceKind(p) !== jumpSlice) return false;
      if (jumpFam) {
        const pool = filter === "shelf" ? s.shelf : (p.colors || []);
        if (!pool.some((c) => familyOf(c) === jumpFam && (filter !== "shelf" || colorOnShelf(c)))) return false;
      }
      if (!q) return true;
      const blob = [p.brand, p.product_line, p.material, ...(p.colors || []).map((c) => c.name)].join(" ").toLowerCase();
      return blob.includes(q);
    });
    rows.sort((a, b) => (b.s.unopened + b.s.opened) - (a.s.unopened + a.s.opened));
    const rolls = rows.reduce((n, r) => n + r.s.unopened, 0);
    const opened = rows.reduce((n, r) => n + r.s.opened, 0);
    $("#invsum").textContent = filter === "shelf"
      ? `架子 ${rows.length} 个料 · ${rolls} 卷未开封 · ${opened} 色有开封`
      : `产品 ${rows.length} 个 · 其中架子 ${rows.filter((r) => r.s.shelf.length).length} 个`;
    if (!rows.length) {
      $("#list").innerHTML = card(`<p class="muted">${filter === "shelf" ? "架子是空的。切到「全部产品」看色卡，或点进产品改库存。" : "没有匹配的产品。"}</p>`);
      return;
    }
    $("#list").innerHTML = rows.map(({ p, s }) => `
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
  };

  render();
  $("#invq").oninput = (e) => { query = e.target.value; render(); };
  $("#invbrand").onchange = (e) => { brand = e.target.value; render(); };
  $("#page").onclick = (e) => {
    const f = e.target.closest("[data-invf]");
    if (f) {
      filter = f.dataset.invf;
      sessionStorage.setItem("pp-inv-filter", filter);
      render();
      return;
    }
    const c = e.target.closest("[data-id]");
    if (c && !e.target.closest("details")) location.hash = "#/materials/" + c.dataset.id;
  };
  $("#add").onclick = (e) => busy(e.currentTarget, async () => {
    const p = await api("/api/products", { method: "POST", body: { brand: $("#b").value, product_line: $("#l").value, material: $("#m").value, bambu_preset_id: $("#new_bpi") ? $("#new_bpi").value : "" } });
    toast("产品已创建", "success");
    location.hash = "#/materials/" + p.id;
  });

  const detailsEl = $("#inv-new-details");
  if (detailsEl) {
    detailsEl.addEventListener("toggle", (e) => {
      if (detailsEl.open) {
        api("/api/presets/sync", { method: "POST" }).then(presets => {
          const sel = $("#new_bpi");
          if (!sel) return;
          let html = `<option value="">-- 请选择关联预设 --</option>`;
          for (const pr of presets) {
            html += `<option value="${pr.id}">${esc(pr.name)}</option>`;
          }
          sel.innerHTML = html;
          sel.onchange = (ev) => {
            const pr = presets.find(x => x.id === ev.target.value);
            if (pr) {
              $("#b").value = pr.vendor || pr.name.split(' ')[0];
              $("#m").value = pr.material || "PLA";
            }
          };
        }).catch(err => console.warn("Failed to load presets for new product", err));
      }
    });
  }
}

async function viewProduct(id) {
    pageLoading("正在打开产品…");
    let p, allClaims, data, spoolRecords;
    try {
      [p, allClaims, spoolRecords] = await Promise.all([
        api("/api/products/" + id),
        api("/api/claims?product_id=" + id),
        api("/api/spools"),
      ]);
      data = p;
    } catch (ex) { pageError(ex); return; }
    const drafts = (allClaims || []).filter(c => c.status === "draft");
    const claims = (allClaims || []).filter(c => c.status !== "draft");
    // 关联拓竹云端规格：拉标记物列表（备注无编号的），默认选中产品已关联值
    api("/api/spools/cloud/sync", { method: "POST" }).then(res => {
      const sel = $("#pbpi");
      if (!sel) return;
      const specs = res.specs || [];
      if (!specs.length) {
        sel.innerHTML = `<option value="">云端没有规格标记物，先去拓竹云端/Studio 建一卷</option>`;
        return;
      }
      sel.innerHTML = `<option value="">-- 未关联 --</option>` + specs.map(sp =>
        `<option value="${sp.cloud_id}" ${sp.cloud_id.toString() === (p.bambu_preset_id || "") ? "selected" : ""}>${esc(sp.name)}（${esc(sp.filament_id)} · ${esc(sp.vendor || "?")}）</option>`).join("");
    }).catch(ex => {
      const sel = $("#pbpi");
      if (sel) sel.innerHTML = `<option value="">规格列表加载失败：${esc(ex.message)}</option>`;
    });
    const conflictKeys = new Set();
  const productSpools = (spoolRecords || []).filter(sp => (p.colors || []).some(c => c.id === sp.color_id));
  const colorOpts = `<option value="">产品级（整系列）</option>` + (p.colors || []).map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join("");
  const colorName = (cid) => (p.colors || []).find((c) => c.id === cid)?.name || "整系列";
  const draftCard = drafts.length === 0 ? "" : card(`
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h2 class="card-title">待确认草稿 <span class="badge badge-warning">${drafts.length}</span></h2>
      <button type="button" class="btn btn-success btn-sm" id="okall">全部确认</button>
    </div>
    <p class="muted">AI 导入只进这里。确认后进档案。编辑改这条草稿，删除是真删。</p>
    <div id="draft-edit" class="hidden mt-2">
      <input type="hidden" id="de-id">
      <div class="row cols-2">
        ${field("来源", selectEl("de-cs", `<option>资料</option><option>Studio</option><option>实测</option>`))}
        ${field("字段", inputEl("de-k", `list="ck-list"`))}
        ${field("值", inputEl("de-v"))}
        ${field("单位", inputEl("de-u"))}
        ${field("原文", inputEl("de-raw"))}
      </div>
      <div class="card-actions">
        <button type="button" class="btn btn-primary btn-sm" id="de-save">保存</button>
        <button type="button" class="btn btn-ghost btn-sm" id="de-cancel">取消</button>
      </div>
    </div>
    <div class="overflow-x-auto"><table class="table">
      <thead><tr><th>来源</th><th>范围</th><th>字段</th><th>值</th><th>原文</th><th></th></tr></thead>
      <tbody>${drafts.map((c) => `<tr>
        <td><span class="badge badge-ghost">${esc(c.source)}</span></td>
        <td>${esc(colorName(c.color_id))}</td>
        <td>${esc(c.key)}</td>
        <td>${esc(c.value)} ${esc(c.unit)}</td>
        <td class="muted">${esc(c.raw || "")}</td>
        <td class="join">
          <button class="btn btn-success btn-xs join-item" data-ok="${c.id}">确认</button>
          <button class="btn btn-ghost btn-xs join-item" data-edit="${c.id}">编辑</button>
          <button class="btn btn-ghost btn-xs join-item" data-delk="${c.id}">删除</button>
        </td></tr>`).join("")}</tbody>
    </table></div>
  `);
  const conflictCard = !(data.conflicts || []).length ? "" : card(`
    <h2 class="card-title">冲突 <span class="badge badge-error">${data.conflicts.length}</span></h2>
    <p class="muted">只比同一维度、同一颜色。喷嘴范围 / 推荐 / 实测 不算互相冲突；不同颜色的实测也不算。</p>
    ${(data.conflicts || []).map((cf) => `<h3 class="font-semibold mt-2">${esc(cf.key)}</h3>
      <ul>${(cf.values || []).map((v) => `<li><span class="badge badge-ghost">${esc(v.source)}</span> ${esc(v.value)} ${esc(v.unit)} <span class="muted">${esc(colorName(v.color_id))}</span></li>`).join("")}</ul>`).join("")}
  `);
  $("#page").innerHTML = `
    ${card(`
      <h1 class="card-title">${esc(p.brand)} ${esc(p.product_line)}</h1>
      ${specStrip(p.card)}
        <div class="row cols-2">
          ${field("关联拓竹云端规格（颜色行【同步】按它建档）", selectEl("pbpi", `<option value="">加载中…</option>`))}
          ${field("细分系列", inputEl("pl", `value="${esc(p.product_line)}" placeholder="如：哑光 / 渐变 (选填)"`))}
        </div>
        <div class="row cols-2">
          ${field("品牌 (自动锁定)", inputEl("pb", `value="${esc(p.brand)}" readonly class="input input-bordered w-full bg-base-200"`))}
          ${field("材质 (自动锁定)", inputEl("pm", `value="${esc(p.material)}" readonly class="input input-bordered w-full bg-base-200"`))}
        </div>
        ${field("备注", textareaEl("pn", p.notes || ""))}
      <div class="card-actions">
        <button class="btn btn-primary" id="savep">保存产品</button>
        <button class="btn btn-error btn-outline" id="delp">删除</button>
      </div>
    `)}
    ${card(`
      <h2 class="card-title">颜色库存（未开封卷 + 是否开封）</h2>
      <div class="row cols-4">
        ${field("商家颜色名（可空可填）", `<input id="cn" class="input input-bordered w-full" list="cn-list" placeholder="下拉已有，或直接填新名字">
          <datalist id="cn-list">${(p.colors || []).map((c) => `<option value="${esc(c.name)}"></option>`).join("")}</datalist>`)}
        ${field("色系（可空）", `<input id="cf" class="input input-bordered w-full" list="cf-list" placeholder="可空，会按颜色名猜">
          <datalist id="cf-list"><option value="白色系"><option value="黑灰色系"><option value="蓝色系"><option value="绿色系"><option value="红粉色系"><option value="黄橙色系"><option value="棕米色系"><option value="紫色系"><option value="金属色系"><option value="透明/自然色系"><option value="多色/效果色系"><option value="未分类"></datalist>`)}
        ${field("未开封", inputEl("cu", `type="number" value="0"`))}
        ${field("开封卷", selectEl("co", `<option value="0">无</option><option value="1">有 1 卷</option>`))}
      </div>
      <div class="card-actions"><button class="btn btn-primary" id="addc">加入颜色</button></div>
      <div class="overflow-x-auto"><table class="table table-zebra">
        <thead><tr><th>颜色</th><th>色系</th><th>未开封</th><th>开封</th><th>均价</th><th></th></tr></thead>
        <tbody>${[...(p.colors || [])].sort((a, b) => Number(colorOnShelf(b)) - Number(colorOnShelf(a)) || (b.unopened - a.unopened)).map((c) => {
          const [bg, isLight] = getDetailedColor(c.name, c.color_family);
          const s = bg ? `style="background:${bg}; color:${isLight?'#000':'#fff'}"` : "";
          const fbg = FAMILY_COLOR[c.color_family];
          const fisLight = LIGHT_FAM.has(c.color_family);
          const fs = fbg ? `style="background:${fbg}; color:${fisLight?'#000':'#fff'}"` : "";
          return `<tr class="${colorOnShelf(c) ? "" : "opacity-50"}"><td><span class="badge badge-sm border-0" ${s}>${esc(c.name)}</span> ${colorOnShelf(c) ? "" : `<span class="badge badge-ghost badge-xs">色卡</span>`}</td><td><span class="badge badge-sm border-0" ${fs}>${esc(c.color_family)}</span></td>
          <td><input class="input input-bordered input-xs w-16" id="u-${c.id}" type="number" min="0" value="${c.unopened}"></td>
          <td><select class="select select-bordered select-xs" id="o-${c.id}"><option value="0"${c.opened ? "" : " selected"}>无</option><option value="1"${c.opened ? " selected" : ""}>有</option></select></td>
          <td>${c.avg_price ? `${yuan(c.avg_price)} <span class="muted">/${c.buy_qty}盘</span>` : "—"}</td>
          <td class="join"><button class="btn btn-primary btn-xs join-item" data-syncc="${c.id}">同步</button><button class="btn btn-ghost btn-xs join-item" data-savec="${c.id}">存</button><button class="btn btn-ghost btn-xs join-item" data-delc="${c.id}">删</button></td></tr>`;
        }).join("")}</tbody>
      </table></div>
    `)}
    ${card(`
      <h2 class="card-title">物理料盘 <span class="badge badge-ghost">${productSpools.length}</span></h2>
      <p class="muted text-sm">颜色行【同步】生成的编号记录，一键同步后实物打标即可对上。称重与报废去「料盘」页操作。</p>
      ${productSpools.length ? `<div class="overflow-x-auto mt-2"><table class="table table-sm table-zebra">
        <thead><tr><th>编号</th><th>颜色</th><th>状态</th><th>重量(g)</th><th>同步时间</th></tr></thead>
        <tbody>${productSpools.map(sp => {
          const c = (p.colors || []).find(c => c.id === sp.color_id);
          const hex = (sp.color_hex || "").toLowerCase();
          const sw = /^[0-9a-f]{6}$/.test(hex) ? `<span class="inline-block w-2.5 h-2.5 rounded-full mr-1 align-middle" style="background:#${hex}"></span>` : "";
          const st = sp.status === "unopened" ? "未开封" : sp.status === "opened" ? "已开封" : "已用完";
          return `<tr><td><span class="badge badge-primary font-mono badge-sm">${esc(sp.short_code)}</span></td>
            <td>${sw}${esc(c ? c.name : "—")}</td>
            <td>${st}</td>
            <td>${sp.net_weight_g}</td>
            <td class="muted text-xs">${sp.last_synced_at ? esc(sp.last_synced_at.replace("T", " ").slice(0, 16)) : "—"}</td></tr>`;
        }).join("")}</tbody></table></div>`
      : `<p class="muted text-sm mt-2">还没有料盘。在上方颜色行点【同步】，即按台账数量到拓竹云端建档并生成编号。</p>`}
    `)}
    ${card(`
      <h2 class="card-title">入库记账</h2>
      <p class="muted text-sm">记单价和盘数，加权算出均价。勾选「加库存」会按小数规则入库（1.5 → 1 封 + 开封）。补记旧货请取消勾选，只进成本账。</p>
      <div class="row cols-4">
        ${field("颜色", selectEl("sin-color", `<option value="">选择颜色</option>` + (p.colors || []).map((c) => {
          const [bg, isLight] = getDetailedColor(c.name, c.color_family);
          return `<option value="${c.id}" ${bg ? `style="background:${bg}; color:${isLight?'#000':'#fff'}"` : ""}>${esc(c.name)}</option>`;
        }).join("")))}
        ${field("盘数", inputEl("sin-qty", `type="number" step="0.1" min="0.1" value="1"`))}
        ${field("单价（元/盘）", inputEl("sin-price", `type="number" step="0.01" min="0" placeholder="27.5"`))}
        ${field("备注", inputEl("sin-note", `placeholder="店铺 / 活动"`))}
      </div>
      <label class="label cursor-pointer justify-start gap-2 py-2"><input id="sin-apply" type="checkbox" class="checkbox checkbox-sm" checked><span class="label-text">同时加库存</span></label>
      <div class="card-actions"><button class="btn btn-primary" id="sinin">记一笔</button></div>
      <p class="muted" id="sinmsg"></p>
      ${(data.stock_ins || []).length ? `<div class="overflow-x-auto"><table class="table table-zebra">
        <thead><tr><th>时间</th><th>颜色</th><th>盘数</th><th>单价</th><th>备注</th></tr></thead>
        <tbody>${(data.stock_ins || []).map((x) => `<tr><td class="muted">${esc((x.created_at || "").replace("T", " ").slice(0, 16))}</td><td>${esc(colorName(x.color_id))}</td><td>${x.qty}</td><td>${yuan(x.unit_price)}</td><td>${esc(x.note || "")}</td></tr>`).join("")}</tbody>
      </table></div>` : ""}
    `)}
    ${card(`
      <h2 class="card-title">资料收集箱 ${(data.inbox || []).filter((x) => x.status === "pending").length ? `<span class="badge badge-warning">${(data.inbox || []).filter((x) => x.status === "pending").length} 待处理</span>` : ""}</h2>
      <p class="muted">商品页、参数表、客服截图先丢这里。叫我处理时我统一抽成草稿，你再确认。单张 ≤8MB，一次最多 10 张。</p>
      <div class="row cols-2">
        ${field("挂到颜色（可空）", selectEl("iboxc", colorOpts))}
        ${field("图片", `<input id="iboxf" type="file" class="file-input file-input-bordered w-full" accept="image/jpeg,image/png,image/webp,image/gif" multiple>`)}
      </div>
      <div class="card-actions"><button class="btn btn-primary" id="iboxup">上传到收集箱</button></div>
      <p class="muted" id="iboxmsg"></p>
      <div class="thumbs">${(data.inbox || []).map((it) => `<figure>
        <img src="${esc(it.url)}" alt="${esc(it.name)}">
        <figcaption>
          <span>${esc(it.name)} <span class="badge badge-sm ${it.status === "pending" ? "badge-warning" : "badge-ghost"}">${it.status === "pending" ? "待处理" : "已处理"}</span></span>
          <button type="button" class="btn btn-ghost btn-xs" data-ibx="${it.id}">删</button>
        </figcaption>
      </figure>`).join("")}</div>
    `)}
    ${draftCard}
    ${conflictCard}
    ${card(`
      <h2 class="card-title">已确认参数（资料 / Studio / 实测 并存）</h2>
      <p class="muted">人手记的直接算确认。喷嘴/热床请分开：范围、推荐、实测（实测挂颜色）。</p>
      <div class="row cols-2">
        ${field("来源", selectEl("cs", `<option>资料</option><option>Studio</option><option>实测</option>`))}
        ${field("范围（可空=整系列，可填新颜色）", `<input id="ccol" class="input input-bordered w-full" list="ccol-list" placeholder="空=整系列">
          <datalist id="ccol-list">${(p.colors || []).map((c) => `<option value="${esc(c.name)}"></option>`).join("")}</datalist>`)}
        ${field("字段", `<input id="ck" class="input input-bordered w-full" list="ck-list" value="喷嘴温度范围">
          <datalist id="ck-list">
            <option value="喷嘴温度范围"><option value="喷嘴推荐温度"><option value="喷嘴实测温度">
            <option value="热床温度范围"><option value="热床推荐温度"><option value="热床实测温度">
            <option value="烘干"><option value="烘干温度范围"><option value="烘干时间">
            <option value="密度"><option value="打印速度上限"><option value="打印速度"><option value="拉伸强度"><option value="弯曲强度">
          </datalist>`)}
        ${field("值", inputEl("cv", `placeholder="范围用 190-230，推荐/实测用单值"`))}
        ${field("单位", inputEl("cuu", `value="°C"`))}
        ${field("原文/出处（可空）", inputEl("craw", `placeholder="客服原话或页码"`))}
      </div>
      <div class="card-actions"><button class="btn btn-primary" id="addk">记一条（已确认）</button></div>
      <div class="overflow-x-auto"><table class="table table-zebra">
        <thead><tr><th>来源</th><th>范围</th><th>字段</th><th>值</th><th></th></tr></thead>
        <tbody>${claims.map((c) => `<tr>
          <td><span class="badge badge-ghost">${esc(c.source)}</span></td>
          <td>${esc(colorName(c.color_id))}</td>
          <td>${esc(c.key)} ${conflictKeys.has(c.key) ? '<span class="badge badge-error badge-sm">冲突</span>' : ""}</td>
          <td>${esc(c.value)} ${esc(c.unit)}</td>
          <td><button class="btn btn-ghost btn-xs" data-delk="${c.id}">删</button></td></tr>`).join("")}</tbody>
      </table></div>
    `)}
    ${card(`
      <h2 class="card-title">预设对照 <span class="badge badge-ghost">${(data.presets || []).length}</span></h2>
      <p class="muted">上传产品预设 JSON / bbsflmt，或 Studio 导出。抽出字段进草稿，和已有资料并排，不覆盖。</p>
      <div class="row cols-2">
        ${field("权威", selectEl("pauth", `<option value="manufacturer_profile">产品预设</option><option value="bambu_system">Studio 系统</option><option value="user_profile">用户/实测</option>`))}
        ${field("文件", `<input id="pfile" type="file" class="file-input file-input-bordered w-full" accept=".json,.bbsflmt,.zip,application/json">`)}
      </div>
      <div class="card-actions"><button class="btn btn-primary" id="pup">上传并对比</button></div>
      <p class="muted" id="pmsg"></p>
      <div class="overflow-x-auto"><table class="table table-zebra">
        <thead><tr><th>名称</th><th>权威</th><th>抽出字段</th><th></th></tr></thead>
        <tbody>${(data.presets || []).map((pr) => `<tr>
          <td>${esc(pr.name)}</td>
          <td><span class="badge badge-ghost">${esc(pr.authority)}</span></td>
          <td class="muted">${esc(Object.entries(pr.fields || {}).map(([k,v]) => k + "=" + v).join(" · "))}</td>
          <td><button class="btn btn-ghost btn-xs" data-pdel="${pr.id}">删</button></td></tr>`).join("")}</tbody>
      </table></div>
    `)}`;
  $("#savep").onclick = (e) => busy(e.currentTarget, async () => {
    await api("/api/products", { method: "POST", body: { id: id, brand: $("#pb").value, product_line: $("#pl").value, material: $("#pm").value, notes: $("#pn").value, bambu_preset_id: $("#pbpi") ? $("#pbpi").value : "" } });
    toast("产品已保存", "success");
    viewProduct(id);
  });
  $("#delp").onclick = (e) => busy(e.currentTarget, async () => {
    if (!confirm("删除这个产品，以及颜色、库存和参数？不能恢复。")) return;
    await api("/api/products/" + id, { method: "DELETE" });
    toast("已删除产品", "success");
    location.hash = "#/materials";
  });
  $("#addc").onclick = (e) => busy(e.currentTarget, async () => {
    const name = $("#cn").value.trim();
    const hit = name ? (p.colors || []).find((c) => c.name === name) : null;
    await api("/api/colors", { method: "POST", body: { id: hit?.id || "", product_id: id, name, color_family: $("#cf").value, unopened: Number($("#cu").value), opened: Number($("#co").value) } });
    toast(hit ? "颜色已更新" : "颜色已加入", "success");
    viewProduct(id);
  });
  if ($("#sin-color")) {
    $("#sin-color").onchange = (e) => {
      const opt = e.target.options[e.target.selectedIndex];
      e.target.style.background = opt.style.background;
      e.target.style.color = opt.style.color;
    };
  }
  $("#sinin").onclick = (e) => busy(e.currentTarget, async () => {
    const color_id = $("#sin-color").value;
    const qty = Number($("#sin-qty").value);
    const unit_price = Number($("#sin-price").value);
    if (!color_id) { toast("先选颜色", "warning"); return; }
    if (!(qty > 0) || !(unit_price >= 0)) { toast("盘数和单价要填对", "warning"); return; }
    await api("/api/stock-ins", { method: "POST", body: { color_id, qty, unit_price, note: $("#sin-note").value, apply: $("#sin-apply").checked } });
    toast("已记账", "success");
    viewProduct(id);
  });
  $("#cs").onchange = () => {
    const k = $("#ck").value;
    if ($("#cs").value === "实测") {
      if (k === "喷嘴温度范围" || k === "喷嘴推荐温度" || k === "喷嘴温度") $("#ck").value = "喷嘴实测温度";
      if (k === "热床温度范围" || k === "热床推荐温度" || k === "热床温度") $("#ck").value = "热床实测温度";
    }
  };
  $("#addk").onclick = (e) => busy(e.currentTarget, async () => {
    await api("/api/claims", { method: "POST", body: { product_id: id, source: $("#cs").value, color_id: resolveColorRef(p, $("#ccol").value), key: $("#ck").value, value: $("#cv").value, unit: $("#cuu").value, raw: $("#craw").value, status: "confirmed" } });
    toast("已记一条", "success");
    viewProduct(id);
  });
  const openDraftEdit = (d) => {
    $("#de-id").value = d.id;
    $("#de-cs").value = d.source || "资料";
    $("#de-k").value = d.key || "";
    $("#de-v").value = d.value || "";
    $("#de-u").value = d.unit || "";
    $("#de-raw").value = d.raw || "";
    $("#draft-edit").classList.remove("hidden");
  };
  if ($("#okall")) $("#okall").onclick = (e) => busy(e.currentTarget, async () => {
    await api("/api/claims/review", { method: "POST", body: { product_id: id, status: "confirmed" } });
    toast("草稿已全部确认", "success");
    viewProduct(id);
  });
  if ($("#de-cancel")) $("#de-cancel").onclick = () => $("#draft-edit").classList.add("hidden");
  if ($("#de-save")) $("#de-save").onclick = (e) => busy(e.currentTarget, async () => {
    const d = drafts.find((x) => x.id === $("#de-id").value);
    if (!d) return;
    await api("/api/claims", { method: "POST", body: {
      id: d.id, product_id: id, color_id: d.color_id || "", source: $("#de-cs").value,
      key: $("#de-k").value, value: $("#de-v").value, unit: $("#de-u").value, raw: $("#de-raw").value, status: "draft",
    } });
    toast("草稿已保存", "success");
    viewProduct(id);
  });
  $("#iboxup").onclick = (e) => busy(e.currentTarget, async () => {
    const files = $("#iboxf").files;
    if (!files || !files.length) { toast("先选图片", "warning"); return; }
    const fd = new FormData();
    if ($("#iboxc").value) fd.append("color_id", $("#iboxc").value);
    for (const f of files) fd.append("files", f);
    toast("上传中…", "info", { sticky: true, id: "ibox" });
    const res = await fetch("/api/products/" + id + "/inbox", { method: "POST", credentials: "include", body: fd });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    toast("已进收集箱", "success", { id: "ibox" });
    viewProduct(id);
  }, "ibox");
  $("#pup").onclick = (e) => busy(e.currentTarget, async () => {
    const f = $("#pfile").files && $("#pfile").files[0];
    if (!f) { toast("先选预设文件", "warning"); return; }
    const fd = new FormData();
    fd.append("file", f);
    fd.append("authority", $("#pauth").value);
    toast("解析中…", "info", { sticky: true, id: "preset" });
    const res = await fetch("/api/products/" + id + "/presets", { method: "POST", credentials: "include", body: fd });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    toast(data.hint || "已进草稿", "success", { id: "preset" });
    viewProduct(id);
  }, "preset");
  $("#page").onclick = async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    try {
      if (btn.dataset.syncc) {
        const cid = btn.dataset.syncc;
        const row = (p.colors || []).find((c) => c.id === cid);
        if (!row) return;
        const total = Number(row.unopened || 0) + (Number(row.opened || 0) > 0 ? 1 : 0);
        if (!total) { toast("这行台账是 0 盘，先把未开封数量填上再同步", "warning"); return; }
        if (!confirm(`将按台账「未开封 ${row.unopened || 0} + 开封 ${row.opened > 0 ? 1 : 0}」去拓竹云端建档并生成编号（已有盘只补差额），继续？`)) return;
        btn.disabled = true;
        try {
          const res = await api("/api/spools/sync-color", { method: "POST", body: { color_id: cid } });
          if (res.codes && res.codes.length) {
            toast(`已建档 ${res.codes.length} 盘，编号：${res.codes.join(", ")}，请写到盘上`, "success", { sticky: true });
          } else {
            toast(res.message || "台账与料盘已一致", "info");
          }
          viewProduct(id);
        } catch (ex) {
          toast(ex.message, "error");
        } finally {
          btn.disabled = false;
        }
        return;
      }
      if (btn.dataset.savec) {
        const cid = btn.dataset.savec;
        const row = (p.colors || []).find((c) => c.id === cid);
        if (!row) return;
        await api("/api/colors", { method: "POST", body: {
          id: cid, product_id: id, name: row.name, color_family: row.color_family,
          unopened: Number($("#u-" + cid).value), opened: Number($("#o-" + cid).value),
        } });
        toast("库存已改", "success");
        viewProduct(id);
      }
      if (btn.dataset.delc) {
        if (!confirm("删除这个颜色和它的库存账？不能恢复。")) return;
        await api("/api/colors?id=" + btn.dataset.delc, { method: "DELETE" });
        toast("已删颜色", "success");
        viewProduct(id);
      }
      if (btn.dataset.delk) {
        if (!confirm("删除这条参数？")) return;
        await api("/api/claims?id=" + btn.dataset.delk, { method: "DELETE" });
        toast("已删参数", "success");
        viewProduct(id);
      }
      if (btn.dataset.ok) { await api("/api/claims/review", { method: "POST", body: { id: btn.dataset.ok, status: "confirmed" } }); toast("已确认", "success"); viewProduct(id); }
      if (btn.dataset.edit) {
        const d = drafts.find((x) => x.id === btn.dataset.edit);
        if (d) openDraftEdit(d);
      }
      if (btn.dataset.ibx) {
        if (!confirm("删除这张图？")) return;
        await api("/api/inbox/" + btn.dataset.ibx, { method: "DELETE" });
        toast("已删图片", "success");
        viewProduct(id);
      }
      if (btn.dataset.pdel) {
        if (!confirm("删除这个预设？")) return;
        await api("/api/presets/" + btn.dataset.pdel, { method: "DELETE" });
        toast("已删预设", "success");
        viewProduct(id);
      }
    } catch (ex) { toast(ex.message, "error"); }
  };
}

async function viewCompare() {
  pageLoading("正在横评…");
  let data;
  try { data = await api("/api/compare"); }
  catch (ex) { pageError(ex); return; }
  const prefer = ["烘干", "烘干温度范围", "烘干时间", "喷嘴温度范围", "喷嘴推荐温度", "热床温度范围", "热床推荐温度", "打印速度上限", "打印速度范围", "打印速度"];
  const rawKeys = Object.keys(data);
  const keys = prefer.filter((k) => data[k]).concat(rawKeys.filter((k) => !prefer.includes(k)));
  $("#page").innerHTML = `
    <h1 class="text-2xl font-bold mb-1">参数横评</h1>
    <p class="text-sm opacity-70 mb-4">已确认条目。同一字段多个值标成冲突，不覆盖。</p>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    ${keys.length === 0 ? "<p>暂无数据</p>" : keys.map((k) => {
      const uniq = new Set(data[k].map((c) => c.value + "|" + c.unit));
      const hit = uniq.size > 1;
      return card(`<h2 class="card-title text-base mb-2">${esc(k)} ${hit ? '<span class="badge badge-error badge-sm">冲突</span>' : ""}</h2>
      <div class="overflow-x-auto"><table class="table table-zebra table-sm">
        <thead><tr><th>产品</th><th>来源</th><th>值</th></tr></thead>
        <tbody>${data[k].map((c) => `<tr><td>${esc(c.product)}</td><td><span class="badge badge-ghost badge-sm">${esc(c.source)}</span></td><td>${esc(c.value)} ${esc(c.unit)}</td></tr>`).join("")}</tbody>
      </table></div>`);
    }).join("")}
    </div>
  `;
}

function swRow(label, role) {
  return `<div class="form-control mb-1">
    <label class="label cursor-pointer p-0">
      <span class="label-text text-base">${label}</span>
      <input type="checkbox" class="toggle toggle-primary" data-t="${role}">
    </label>
  </div>`;
}

async function viewMachine() {
  if (!$("#mach")) pageLoading("正在连接机台…");
  const ensureShell = () => {
    if ($("#mach")) return;
    $("#page").innerHTML = `<div id="mach" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      ${card(`<h1 class="card-title">机台（只读）</h1><div id="mach-stats"></div>`)}
      ${card(`
        <h2 class="card-title">监控 + 补光</h2>
        <div class="mb-2"><button type="button" class="btn btn-sm btn-primary" id="ez-play">▶ 播放</button> <button type="button" class="btn btn-sm btn-outline" id="ez-stop">■ 停止</button></div><div id="ezviz"></div>
        ${swRow("补光灯", "light")}
      `)}
      ${card(`
        <h2 class="card-title">净化器</h2>
        ${swRow("仓内长开", "box_always")}
        ${swRow("仓内打印加强", "box_print")}
        ${swRow("车间有人", "room")}
      `)}
      ${card(`<h2 class="card-title">仓外空气</h2><div id="mach-air"></div>`)}
    </div>`;
    $("#mach").onchange = async (e) => {
      const t = e.target.closest("[data-t]");
      if (!t) return;
      const role = t.dataset.t;
      const on = t.checked;
      t.disabled = true;
      try {
        await api("/api/actuators/" + role, { method: "POST", body: { on } });
        toast("已发送", "success", { id: "mach" });
      } catch (ex) {
        toast(ex.message, "error", { id: "mach" });
        t.checked = !on;
      } finally {
        t.disabled = false;
      }
    };
  };
  let spools = [];
  const draw = async () => {
    let d;
    try { d = await api("/api/machine"); }
    catch (ex) { toast(ex.message, "error", { id: "mach" }); if (!$("#mach")) pageError(ex); return; }
    ensureCatalog();
    try { spools = await api("/api/spools"); } catch(e) {}
    ensureShell();
    const b = d.bambu || {};
    const air = d.air || {};
    
    if (document.querySelector("[data-t]")) {
      const qs = (sel) => document.querySelector(sel);
      qs("[data-t='light']") && (qs("[data-t='light']").checked = !!air.light);
      qs("[data-t='box_always']") && (qs("[data-t='box_always']").checked = !!air.box_always);
      qs("[data-t='box_print']") && (qs("[data-t='box_print']").checked = !!air.box_print);
      qs("[data-t='room']") && (qs("[data-t='room']").checked = !!air.room);
    }

    const printing = !!d.printing;
    const boost = b.print_boost_active ? `<span class="badge badge-warning">打印加强开着</span>` : "";
    let spdStr = "";
    if (b.spd_lvl != null && String(b.spd_lvl) !== "2") {
        const lvlMap = {"1": "静音 50%", "3": "狂暴 124%", "4": "荒野狂飙 166%"};
        spdStr = `<span class="badge badge-secondary">${lvlMap[String(b.spd_lvl)] || "未知速度"}</span>`;
    }
    $("#mach-stats").innerHTML = `
      <p>${b.connected ? '<span class="badge badge-success">拓竹 MQTT 已连接</span>' : `<span class="badge badge-error badge-outline">未连接</span> <span class="muted">${esc(b.error || "")}</span>`}
        ${printing ? `<span class="badge badge-success">打印中</span>` : `<span class="badge badge-ghost">${esc(b.gcode_state || b.stage || "空闲")}</span>`}
        ${boost} ${spdStr}</p>
      ${(() => {
          const formatTemp = (t) => t != null ? Math.round(Number(t)) : "—";
          const formatTime = (mins) => {
              if (mins == null) return "—";
              const m = parseInt(mins, 10);
              if (isNaN(m)) return "—";
              if (m < 60) return `${m} 分钟`;
              return `${Math.floor(m/60)}小时${m%60}分钟`;
          };
          const calcEnd = (mins) => {
              if (mins == null) return "";
              const m = parseInt(mins, 10);
              if (isNaN(m) || m <= 0) return "";
              const now = new Date();
              const end = new Date(now.getTime() + m * 60000);
              const pad = (n) => n.toString().padStart(2, "0");
              const isNextDay = end.getDate() !== now.getDate();
              return `<div class="mt-1 text-xs opacity-70">预计 ${isNextDay ? "次日 " : ""}${pad(end.getHours())}:${pad(end.getMinutes())} 结束</div>`;
          };
          return `
      <div class="stats stats-vertical lg:stats-horizontal shadow-sm bg-base-200 w-full">
        <div class="stat">
          <div class="stat-title">热床</div>
          <div class="stat-value text-primary">${formatTemp(b.bed_temp)}<span class="text-lg">°C</span></div>
          <div class="stat-desc">目标 ${formatTemp(b.bed_target)}°C</div>
        </div>
        <div class="stat">
          <div class="stat-title">喷嘴</div>
          <div class="stat-value">${formatTemp(b.nozzle_temp)}<span class="text-lg">°C</span></div>
          <div class="stat-desc">目标 ${formatTemp(b.nozzle_target)}°C</div>
        </div>
        <div class="stat">
          <div class="stat-title">进度</div>
          <div class="stat-value">${b.progress ?? "—"}%</div>
          <div class="stat-desc">剩余 ${formatTime(b.remaining)}${calcEnd(b.remaining)}</div>
        </div>
      </div>`;
      })()}
      ${(() => {
        const bmap = {
          "GFA00": "Bambu PLA Basic", "GFA01": "Bambu PLA Matte", "GFA02": "Bambu PLA Metal",
          "GFA03": "Bambu PLA Silk", "GFA04": "Bambu PLA Tough", "GFA05": "Bambu PLA Sparkle",
          "GFA07": "Bambu PLA Marble", "GFA08": "Bambu PLA Aero", "GFA09": "Bambu PLA CF",
          "GFA11": "Bambu PLA Galaxy", "GFB00": "Bambu ABS", "GFB01": "Bambu ASA",
          "GFC00": "Bambu PC", "GFC01": "Bambu PC",
          "GFE00": "Bambu TPU 95A", "GFF00": "Bambu PVA",
          "GFG00": "Bambu PETG Basic", "GFG50": "Bambu PETG-CF",
          "GFN03": "Bambu PA-CF", "GFN04": "Bambu PAHT-CF", "GFN05": "Bambu PA6-CF",
          "GFU01": "Bambu Support G", "GFU02": "Bambu Support W"
        };
        const getBrand = (t) => {
          if (t.tray_sub_brands) return t.tray_sub_brands;
          if (t.tray_info_idx && bmap[t.tray_info_idx]) return bmap[t.tray_info_idx];
          return t.tray_type || "";
        };
        const rgbOf = (hex) => {
          const s = String(hex || "").substring(0, 6);
          if (!/^[0-9a-fA-F]{6}$/.test(s)) return [136, 136, 136];
          return [parseInt(s.substring(0, 2), 16), parseInt(s.substring(2, 4), 16), parseInt(s.substring(4, 6), 16)];
        };
        const getColorName = (hex) => {
          // 按 HSL 色相命名；16 色调色板会把 A03CF7 这类紫色误判成浅灰。
          const [r, g, b] = rgbOf(hex);
          const max = Math.max(r, g, b), min = Math.min(r, g, b);
          const d = max - min;
          const s = max === 0 ? 0 : d / max;
          const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
          if (s < 0.14) {
            if (lum > 0.85) return "白色";
            if (lum > 0.62) return "浅灰";
            if (lum > 0.3) return "灰色";
            if (lum > 0.12) return "深灰";
            return "黑色";
          }
          let h = 0;
          if (d !== 0) {
            if (max === r) h = ((g - b) / d) % 6;
            else if (max === g) h = (b - r) / d + 2;
            else h = (r - g) / d + 4;
            h = Math.round(h * 60);
            if (h < 0) h += 360;
          }
          const pre = lum > 0.72 ? "浅" : (lum < 0.3 ? "深" : "");
          if (h < 14 || h >= 345) return pre + "红色";
          if (h < 40) return pre + "橙色";
          if (h < 68) return pre + "黄色";
          if (h < 95) return "黄绿色";
          if (h < 160) return pre + "绿色";
          if (h < 200) return pre + "青色";
          if (h < 255) return pre + "蓝色";
          if (h < 292) return pre + "紫色";
          return pre + "玫红色";
        };
        // 拓竹闲置时外部料架会占位上报 #A0A0A0 一类的灰，不能当成真实耗材。
        const isPlaceholderGray = (hex) => {
          const [r, g, b] = rgbOf(hex);
          return Math.abs(r - g) < 14 && Math.abs(g - b) < 14 && r >= 135 && r <= 190;
        };
        const matchSpool = (hex, trayType) => {
          const [cR, cG, cB] = rgbOf(hex);
          const tt = String(trayType || "").toLowerCase();
          let best = null, minDist = Infinity;
          for (const sp of (spools || [])) {
            if (sp.status !== "opened") continue;
            const [sR, sG, sB] = rgbOf(sp.color_hex || "");
            let dist = (cR-sR)**2 + (cG-sG)**2 + (cB-sB)**2;
            const mType = (sp.bambu_filament_name || "").toLowerCase();
            if (tt && mType.includes(tt)) dist -= 20000;
            if (dist < minDist) { minDist = dist; best = sp; }
          }
          return (best && minDist < 20000) ? best : null;
        };
        const spoolBadge = (prefix, sp, hex, brand) => {
          const fname = sp ? (sp.bambu_filament_name || getColorName(sp.color_id)) : getColorName(hex);
          const label = sp ? `[${sp.short_code}] ${fname}` : `${getColorName(hex)}${brand ? " " + brand : ""}`;
          return `<span class="badge badge-outline text-xs" style="border-color:#${String(hex||"888888").substring(0,6)}">${esc(prefix)}: ${esc(label)}</span>`;
        };
        const gcode = String(b.gcode_state || "").toUpperCase();
        const idleLike = ["IDLE", "FINISH", "FINISHED", "FAILED"].includes(gcode);
        let filamentStr = "";
        const tn = b.tray_now != null ? String(b.tray_now) : "";
        if (tn && tn !== "255") {
          if (tn === "254") {
            const col = (b.vt_tray?.tray_color || "").substring(0, 6);
            if (!b.vt_tray || (idleLike && isPlaceholderGray(col))) {
              // 闲置 + 占位灰 = 外部料架根本没挂料，别伪装成已装耗材。
              filamentStr = `　<span class="badge badge-ghost text-xs">进料: 空（外部料架未挂料）</span>`;
            } else {
              const sp = matchSpool(col, b.vt_tray.tray_type);
              filamentStr = "　" + spoolBadge("料架", sp, col, getBrand(b.vt_tray));
            }
          } else if (b.ams?.ams?.length > 0) {
            outer:
            for (const a of b.ams.ams) {
              for (const t of (a.tray || [])) {
                if (String(t.id) !== tn) continue;
                const col = (t.tray_color || "888888").substring(0, 6);
                const sp = matchSpool(col, t.tray_type);
                filamentStr = "　" + spoolBadge(`AMS-${tn}`, sp, col, getBrand(t));
                break outer;
              }
            }
          }
        }
        // 闲置时顺带展示 AMS 整机装载，替代被 254 占位误导的"当前料盘"。
        let amsStr = "";
        if (idleLike && b.ams?.ams?.length > 0) {
          const chips = [];
          for (const a of b.ams.ams) {
            for (const t of (a.tray || [])) {
              const col = (t.tray_color || "").substring(0, 6);
              if (!col || !t.tray_type) continue;
              chips.push(`<span class="badge badge-ghost badge-xs" style="border-color:#${col}">${esc(t.tray_type)} ${esc(getColorName(col))}</span>`);
              if (chips.length >= 8) break;
            }
            if (chips.length >= 8) break;
          }
          if (chips.length) amsStr = `<p class="muted mt-1 text-xs">AMS 在位：${chips.join(" ")}</p>`;
        }
        return `<p class="muted mt-2">层数 ${b.layer ?? "—"} / ${b.total_layer ?? "—"}　${esc(b.subtask || "")}${filamentStr}</p>${amsStr}`;
      })()}
    `;
    let airTs = Number(air.ts);
    if (airTs > 1e12) airTs /= 1000;
    const stale = airTs ? (Date.now() / 1000 - airTs) > 15 * 60 : false;
    $("#mach-air").innerHTML = `
      <p>PM2.5 <strong>${air.pm25 ?? "—"}</strong>　室温 ${air.t_c ?? "—"} ℃　湿度 ${air.rh ?? "—"} %　有人 ${air.presence ?? "—"}</p>
      <p class="${stale ? "text-warning" : "muted"}">${air.ts ? `探头 ${esc(airAgeText(air.ts))}${stale ? " · 超过 15 分钟没报" : ""}` : "还没有探头数据"}</p>`;
    
    if (d.ezviz?.configured && $("#ezviz")) {
      const playBtn = $("#ez-play");
      const stopBtn = $("#ez-stop");
      if (playBtn && !playBtn.onclick) {
        playBtn.onclick = async () => {
          if (window.__ez) return; // Already playing
          try {
            playBtn.disabled = true;
            playBtn.textContent = "正在获取视频流...";
            const cam = await api("/api/camera");
            const ezvizDiv = document.getElementById("ezviz");
            const ezW = ezvizDiv.clientWidth;
            const rot = d.ezviz?.rotation || "0";
            const isPortrait = (rot === "90" || rot === "-90");
            const finalH = isPortrait ? Math.round(ezW * 16 / 9) : Math.round(ezW * 9 / 16);
            
            const cropVals = (d.ezviz?.crop || "0,0,0,0").split(",").map(x => Number(x) || 0);
            const cT = Math.max(0, Math.min(99, cropVals[0]));
            const cB = Math.max(0, Math.min(99, cropVals[1]));
            const cL = Math.max(0, Math.min(99, cropVals[2]));
            const cR = Math.max(0, Math.min(99, cropVals[3]));
            const fW = 1 - (cL + cR) / 100;
            const fH = 1 - (cT + cB) / 100;
            
            const baseAspect = isPortrait ? 9/16 : 16/9;
            const cropAspect = baseAspect * (fW / fH);
            const displayH = Math.round(ezW / cropAspect);
            
            ezvizDiv.style.height = displayH + "px";
            ezvizDiv.style.position = "relative";
            ezvizDiv.style.overflow = "hidden";
            
            const cropWrapper = document.createElement("div");
            cropWrapper.style.position = "absolute";
            const uncroppedW = ezW / fW;
            const uncroppedH = displayH / fH;
            cropWrapper.style.width = uncroppedW + "px";
            cropWrapper.style.height = uncroppedH + "px";
            cropWrapper.style.left = - (cL / 100 * uncroppedW) + "px";
            cropWrapper.style.top = - (cT / 100 * uncroppedH) + "px";
            ezvizDiv.appendChild(cropWrapper);
            
            const rotWrapper = document.createElement("div");
            rotWrapper.style.position = "absolute";
            cropWrapper.appendChild(rotWrapper);
            
            const sub = document.createElement("div");
            sub.id = "ezviz-sub";
              sub.style.width = "100%";
              sub.style.height = "100%";
            rotWrapper.appendChild(sub);
            
            const playerW = isPortrait ? uncroppedH : uncroppedW;
            const playerH = isPortrait ? uncroppedW : uncroppedH;
            
            if (rot === "90") {
               rotWrapper.style.transform = "rotate(90deg)";
               rotWrapper.style.transformOrigin = "top left";
               rotWrapper.style.width = playerW + "px";
               rotWrapper.style.height = playerH + "px";
               rotWrapper.style.left = uncroppedW + "px";
               rotWrapper.style.top = "0";
            } else if (rot === "-90") {
               rotWrapper.style.transform = "rotate(-90deg)";
               rotWrapper.style.transformOrigin = "top left";
               rotWrapper.style.width = playerW + "px";
               rotWrapper.style.height = playerH + "px";
               rotWrapper.style.top = uncroppedH + "px";
               rotWrapper.style.left = "0";
            } else if (rot === "180") {
               rotWrapper.style.transform = "rotate(180deg)";
               rotWrapper.style.transformOrigin = "center center";
               rotWrapper.style.width = "100%";
               rotWrapper.style.height = "100%";
               rotWrapper.style.left = "0";
               rotWrapper.style.top = "0";
            } else {
               rotWrapper.style.width = "100%";
               rotWrapper.style.height = "100%";
               rotWrapper.style.left = "0";
               rotWrapper.style.top = "0";
            }
            
            const iframeSrc = `https://open.ys7.com/ezopen/h5/iframe?url=${encodeURIComponent(cam.url)}&accessToken=${encodeURIComponent(cam.accessToken)}&autoplay=1&audio=0`;
            $("#ezviz-sub").innerHTML = `<iframe src="${iframeSrc}" width="100%" height="100%" frameborder="0" allowfullscreen></iframe>`;
            window.__ez = { stop: () => { $("#ezviz-sub").innerHTML = ""; } };
            
            playBtn.textContent = "▶ 播放";
            playBtn.disabled = false;
          } catch (e) { 
            toast(e.message, "error", { id: "mach" }); 
            playBtn.textContent = "▶ 播放失败";
            playBtn.disabled = false;
          }
        };
        stopBtn.onclick = () => {
          if (window.__ez) {
            window.__ez.stop();
            window.__ez = null;
            $("#ezviz").innerHTML = "";
            $("#ezviz").style.height = "";
          }
        };
      }
    }

  };
  await draw();
  if (window.__machTimer) clearInterval(window.__machTimer);
  window.__machTimer = setInterval(() => {
    if (route() !== "/machine" || document.hidden) return;
    draw();
  }, 15000);
}

async function viewAir() {
  pageLoading("正在读取空气…");
  let rows;
  try { rows = await api("/api/air"); }
  catch (ex) { pageError(ex); return; }
  if (!Array.isArray(rows)) rows = [];
  const latest = rows[0];
  const pm = latest?.data?.pm25 ?? latest?.data?.room?.pm25;
  let band = "尚无数据";
  let badge = "badge-ghost";
  if (pm != null) {
    if (pm <= 35) { band = "优"; badge = "badge-success"; }
    else if (pm <= 75) { band = "良"; badge = "badge-warning"; }
    else { band = "超标倾向"; badge = "badge-error"; }
  }
  const latestTs = latest?.ts;
  let latestN = Number(latestTs);
  if (latestN > 1e12) latestN /= 1000;
  const stale = latestN ? (Date.now() / 1000 - latestN) > 15 * 60 : false;
  $("#page").innerHTML = card(`
    <h1 class="card-title">仓外空气</h1>
    <p>最新 PM2.5：<strong>${pm ?? "—"}</strong> µg/m³　<span class="badge ${badge}">${band}</span>
      ${latestTs ? `<span class="${stale ? "text-warning" : "muted"}"> · ${esc(airAgeText(latestTs))}${stale ? "（超过 15 分钟没报）" : ""}</span>` : ""}</p>
    <p class="muted">对照 GB/T 18883 日均 50 µg/m³，仅供参考。POST /api/ingest/air 上报。</p>
    <div class="overflow-x-auto"><table class="table table-zebra">
      <thead><tr><th>时间</th><th>区</th><th>数据</th></tr></thead>
      <tbody>${rows.slice(0, 40).map((r) => `<tr><td>${new Date(r.ts * 1000).toLocaleString()}</td><td><span class="badge badge-ghost">${esc(r.zone)}</span></td><td><code>${esc(JSON.stringify(r.data))}</code></td></tr>`).join("")}</tbody>
    </table></div>
  `);
}

async function viewSettings(me) {
  $("#page").classList.add("page-wide");
  pageLoading("正在打开设置…");
  let s;
  try { s = await api("/api/settings"); }
  catch (ex) { pageError(ex); return; }
  
  let hookUrl = window.location.protocol + "//" + window.location.host + "/api/wecom/verify";
  let serverIp = "你的服务器公网IP";
  try { 
    let res = await fetch("/api/server-ip").then(r => r.text()); 
    if (res.trim() !== "") serverIp = res;
  } catch(e) {}

  $("#page").innerHTML = `
    <div class="settings-head">
      <div>
        <h1 class="card-title">设置</h1>
        <p class="muted">拷给第二个人：跑起来只填这一页。密码框留空表示不改。结果在右下角弹出。</p>
      </div>
      <button type="button" class="btn btn-primary" id="sa">保存全部设置</button>
    </div>
    <div class="masonry-grid">
    ${card(`
      <h2 class="card-title">登录</h2>
      <div class="row cols-2">
        ${field("站点名称", inputEl("st", `value="${esc(s.site.title)}"`))}
        ${field("用户名", inputEl("su", `value="${esc(me.username)}"`))}
        ${field("原密码", inputEl("so", `type="password"`))}
        ${field("新密码", inputEl("sn", `type="password"`))}
      </div>
      <div class="card-actions">
        <button class="btn btn-primary" id="ssite">保存站点名</button>
        <button class="btn btn-ghost" id="spw">更新用户名密码</button>
      </div>
    `)}
    ${card(`
      <h2 class="card-title">拓竹云（只读）</h2>
      <p class="muted">中国区现在几乎都必须验证码。顺序：保存账号 → 发送验证码 → 填码登录。以后会记住 token，不必每次验证。</p>
      <div class="row cols-2">
        ${field("地区", inputEl("br", `value="${esc(s.bambu.region)}"`))}
        ${field("打印机 SN", inputEl("bsn", `value="${esc(s.bambu.printer_sn)}"`))}
        ${field("账号（手机或邮箱）", inputEl("ba", `value="${esc(s.bambu.account)}"`))}
        ${field("密码", inputEl("bp", `type="password" placeholder="不改请留空"`))}
        ${field("短信/邮箱验证码", inputEl("bc", `placeholder="6 位"`))}
        ${field("或粘贴 accessToken", inputEl("btok", `type="password" placeholder="可选，高级用法"`))}
      </div>
      <div class="card-actions flex-wrap">
        <button class="btn btn-ghost" id="tb">保存并尝试登录</button>
        <button class="btn btn-ghost" id="bcode">发送验证码</button>
        <button class="btn btn-primary" id="bver">用验证码登录</button>
        <button class="btn btn-ghost" id="btoken">用 Token 登录</button>
      </div>
    `)}
    ${card(`
      <h2 class="card-title">易微联</h2>
      <p class="muted">云服务器从易微联云开关插座，手机 App 继续能用。三联继电器会拆成 3 路，点一下绑定，不用手抄 ID。</p>
      <ul class="steps steps-vertical lg:steps-horizontal w-full">
        <li class="step step-primary">填 App 同一套账号</li>
        <li class="step step-primary">登录并拉设备</li>
        <li class="step">点选绑定并试开关</li>
      </ul>
      <div class="row cols-2">
        ${field("地区（中国填 cn）", inputEl("er", `value="${esc(s.ewelink.region)}"`))}
        ${field("手机或邮箱", inputEl("ea", `value="${esc(s.ewelink.account)}" placeholder="138xxxx 或邮箱"`))}
        ${field("密码", inputEl("ep", `type="password" placeholder="已保存则留空"`))}
        ${field("打印后加强分钟", inputEl("emin", `type="number" value="${s.automations.print_boost_minutes}"`))}
      </div>
      ${field("或粘贴 Access Token（账号密码 407 时用）", inputEl("etok", `type="password" placeholder="从 web.ewelink.cc 复制 Bearer 后面那段"`))}
      <div class="collapse collapse-arrow bg-base-200 border border-base-300">
        <input type="checkbox" />
        <div class="collapse-title">高级：自备 APPID（一般必须留空）</div>
        <div class="collapse-content">
          <div class="row cols-2">
            ${field("APPID", inputEl("eid", `value="" placeholder="留空"`))}
            ${field("APPSECRET", inputEl("es", `type="password" placeholder="留空"`))}
          </div>
          <p class="muted">开发者中心的官方 APPID 走账号密码会报 407。这里留空，用内置凭证。</p>
        </div>
      </div>
      <div class="card-actions flex-wrap">
        <button class="btn btn-primary" id="te">登录并拉设备</button>
        <button class="btn btn-ghost" id="ewtok">用 Token 登录</button>
        <button class="btn btn-ghost" id="ewsave">只保存账号</button>
      </div>
      <div class="bind-summary" id="ebound">
        ${bindRow("补光灯", "el", s.ewelink.light)}
        ${bindRow("仓内长开", "eba", s.ewelink.box_always)}
        ${bindRow("仓内打印加强", "ebp", s.ewelink.box_print)}
        ${bindRow("车间有人", "ero", s.ewelink.room)}
      </div>
      <div id="elist"></div>
    `)}
    ${card(`
      <h2 class="card-title">萤石</h2>
      <p class="text-sm muted mb-2">
        <a href="https://open.ys7.com/console/application.html" target="_blank" class="link">👉 点此获取 AppKey 和 Secret</a>
        <span class="mx-2">|</span>
        <a href="https://open.ys7.com/console/device.html" target="_blank" class="link">👉 点此查看设备绑定与序列号</a>
        <br>
        <span class="text-xs">注意：在“应用详情”中，应用名称可随便填，但必须配置才能拿到密钥。</span>
      </p>
      <div class="row cols-2">
        ${field("AppKey", inputEl("zk", `value="${esc(s.ezviz.app_key)}"`))}
        ${field("Secret", inputEl("zs", `type="password" placeholder="不改请留空"`))}
        ${field("设备序列号", inputEl("zd", `value="${esc(s.ezviz.device_serial)}"`))}
        ${field("通道", inputEl("zc", `value="${esc(s.ezviz.channel)}"`))}
        ${field("设备验证码", inputEl("zvc", `value="${esc(s.ezviz.verify_code || "")}" type="password" placeholder="设备底部的6位大写字母"`))}
        ${field("画面旋转", `<select id="zr" class="select select-bordered w-full">
          <option value="" ${!s.ezviz.rotation || s.ezviz.rotation === "" || s.ezviz.rotation === "0" ? "selected" : ""}>正常</option>
          <option value="90" ${s.ezviz.rotation === "90" ? "selected" : ""}>向右旋转 90°</option>
          <option value="-90" ${s.ezviz.rotation === "-90" ? "selected" : ""}>向左旋转 90°</option>
          <option value="180" ${s.ezviz.rotation === "180" ? "selected" : ""}>旋转 180°</option>
        </select>`)}
      </div>
      <div class="row cols-4 mt-2">
        ${(() => {
          const _c = (s.ezviz.crop || "0,0,0,0").split(",");
          return field("截上(%)", inputEl("zc_t", `type="number" value="${esc(_c[0]||"0")}"`)) +
                 field("截下(%)", inputEl("zc_b", `type="number" value="${esc(_c[1]||"0")}"`)) +
                 field("截左(%)", inputEl("zc_l", `type="number" value="${esc(_c[2]||"0")}"`)) +
                 field("截右(%)", inputEl("zc_r", `type="number" value="${esc(_c[3]||"0")}"`));
        })()}
      </div>
      <div class="card-actions"><button class="btn btn-ghost" id="tz">保存并测试萤石</button></div>
    `)}
    ${card(`
      <h2 class="card-title">消息通知</h2>
      <p class="text-sm muted">在首层开始，以及打印完成 10 分钟后自动抓取监控图推送。</p>
      
      <div class="mt-2">
        
      
      <div class="mt-4">
        <div class="font-bold border-b pb-1 mb-2">消息通知 (企业微信)</div>
        <p class="text-xs muted mb-3" style="line-height:1.5;">
          <b>企业微信自建应用推送 (完全免费，直接在微信显示监控大图)</b><br>
          1. <a href="https://work.weixin.qq.com" target="_blank" class="link">注册/登录企业微信后台</a> -> 应用管理 -> 创建应用。<br>
          2. 在“接收消息”处填写 URL: <code id="wecom-webhook-url">${hookUrl}</code>，获取 <b>Token</b> 和 <b>EncodingAESKey</b>。<br>
          3. 将 <b>企业ID</b>, <b>Secret</b>, <b>AgentID</b>, <b>AESKey</b> 填入下方，点击“保存通知设置”。<br>
          4. 回到企业微信页面点击“保存”。验证通过后，将“企业可信IP”设置为 <code id="wecom-server-ip">${serverIp}</code>。
        </p>
        <div class="row cols-5 mb-3">
          ${field("企业ID (CorpID)", inputEl("wcCorp", `value="${esc(s.automations.wecom_corpid || "")}" placeholder="ww..."`))}
          ${field("应用Secret", inputEl("wcSec", `type="password" placeholder="留空不改"`))}
          ${field("应用AgentID", inputEl("wcAgent", `value="${esc(s.automations.wecom_agentid || "")}" placeholder="1000002"`))}
          ${field("EncodingAESKey", inputEl("wcAES", `type="password" placeholder="用于过检URL验证"`))}
          ${field("接收人账号(留空则发全体)", inputEl("wcTo", `value="${esc(s.automations.wecom_touser || "")}" placeholder="@all 或 账号ID"`))}
        </div>
      </div>
      
      <div class="card-actions mt-3">
        <button class="btn btn-primary" id="savewh">保存通知设置</button>
        <button class="btn" id="testwh" style="margin-left: 8px;">发送测试推送</button>
      </div>
    `)}
    ${card(`
      <h2 class="card-title">空气探头 / AI 令牌</h2>
      <p>ESP32：<code>POST /api/ingest/air</code>　AI 只读：<code>GET /api/ai/materials</code>　起草：<code>POST /api/ai/drafts</code></p>
      <p class="muted">Authorization: Bearer 令牌。AI 令牌只能写草稿，不能确认、不能改库存。</p>
      ${field("空气令牌", inputEl("at", `value="${esc(s.air.token)}"`))}
      ${field("AI 令牌", inputEl("ait", `value="${esc(s.ai?.token || "")}"`))}
    `)}
    </div>`;
  const collect = () => ({
    site: { title: $("#st").value },
    bambu: { region: $("#br").value, account: $("#ba").value, password: $("#bp").value, printer_sn: $("#bsn").value },
    ewelink: { region: $("#er").value, account: $("#ea").value, password: $("#ep").value, app_id: $("#eid")?.value || "", app_secret: $("#es")?.value || "",
      light: $("#el").value, box_always: $("#eba").value, box_print: $("#ebp").value, room: $("#ero").value },
    ezviz: { app_key: $("#zk").value, app_secret: $("#zs").value, device_serial: $("#zd").value, channel: $("#zc").value, verify_code: $("#zvc")?.value || "", rotation: $("#zr")?.value || "", crop: `${$("#zc_t")?.value||0},${$("#zc_b")?.value||0},${$("#zc_l")?.value||0},${$("#zc_r")?.value||0}` },
    air: { token: $("#at").value },
    ai: { token: $("#ait")?.value || "" },
    automations: { box_always_on: true, print_boost_minutes: Number($("#emin").value), room_on_presence: true, wecom_corpid: $("#wcCorp")?.value || "", wecom_secret: $("#wcSec")?.value || "", wecom_agentid: $("#wcAgent")?.value || "", wecom_aeskey: $("#wcAES")?.value || "", wecom_touser: $("#wcTo")?.value || "" },
  });
  const saveSite = async () => {
    await api("/api/settings", { method: "PUT", body: collect() });
    updateAppTitle($("#st").value.trim());
    toast("设置已保存", "success", { id: "set" });
  };
  $("#ssite").onclick = (e) => busy(e.currentTarget, async () => {
    const title = $("#st").value.trim() || "PandaSpool";
    await api("/api/settings", { method: "PUT", body: { ...collect(), site: { title } } });
    updateAppTitle(title);
    toast("站点名称已生效", "success", { id: "set" });
  }, "set");
  $("#savewh").onclick = (e) => busy(e.currentTarget, async () => {
    await api("/api/settings", { method: "PUT", body: collect() });
    const d = await api("/api/settings/test/wecom", { method: "POST", body: {} });
    toast(d.hint || "已保存", "success", { id: "set" });
  }, "set");
  $("#testwh").onclick = (e) => busy(e.currentTarget, async () => {
    await api("/api/settings", { method: "PUT", body: collect() });
    await api("/api/notify/test", { method: "POST" });
    toast("测试推送已下发，请看手机企业微信", "success", { id: "set" });
  }, "set");
  $("#sa").onclick = (e) => busy(e.currentTarget, saveSite, "set");
  $("#spw").onclick = (e) => busy(e.currentTarget, async () => {
    await api("/api/settings/password", { method: "POST", body: { username: $("#su").value, old_password: $("#so").value, new_password: $("#sn").value } });
    toast("登录已更新", "success", { id: "set" });
  }, "set");
  $("#tb").onclick = (e) => busy(e.currentTarget, async () => {
    toast("正在保存并尝试登录拓竹…", "info", { sticky: true, id: "bambu" });
    await api("/api/settings", { method: "PUT", body: collect() });
    const d = describeStatus(await api("/api/settings/test/bambu", { method: "POST", body: {} }));
    toast(d.t, d.k, { id: "bambu" });
  }, "bambu");
  $("#bcode").onclick = (e) => busy(e.currentTarget, async () => {
    toast("正在发送验证码…", "info", { sticky: true, id: "bambu" });
    await api("/api/settings", { method: "PUT", body: collect() });
    const r = await api("/api/settings/bambu/send-code", { method: "POST", body: {} });
    toast(r.hint || "验证码已发送", "success", { id: "bambu" });
  }, "bambu");
  $("#bver").onclick = (e) => busy(e.currentTarget, async () => {
    toast("正在用验证码登录…", "info", { sticky: true, id: "bambu" });
    await api("/api/settings", { method: "PUT", body: collect() });
    const d = describeStatus(await api("/api/settings/bambu/verify-code", { method: "POST", body: { code: $("#bc").value } }));
    toast(d.t, d.k, { id: "bambu" });
  }, "bambu");
  $("#btoken").onclick = (e) => busy(e.currentTarget, async () => {
    toast("正在用 Token 登录…", "info", { sticky: true, id: "bambu" });
    await api("/api/settings", { method: "PUT", body: collect() });
    const d = describeStatus(await api("/api/settings/bambu/token", { method: "POST", body: { access_token: $("#btok").value } }));
    toast(d.t, d.k, { id: "bambu" });
  }, "bambu");
  const renderDevices = (devs) => {
    const roles = [
      ["light", "补光"],
      ["box_always", "仓内长开"],
      ["box_print", "打印加强"],
      ["room", "车间有人"],
    ];
    const bound = { light: $("#el").value, box_always: $("#eba").value, box_print: $("#ebp").value, room: $("#ero").value };
    if (!devs || !devs.length) {
      $("#elist").innerHTML = `<p class="muted">账号下没有设备。先在手机易微联 App 里配网，再点登录。</p>`;
      return;
    }
    $("#elist").innerHTML = `<div class="overflow-x-auto"><table class="table table-zebra">
      <thead><tr><th>设备 / 通道</th><th>状态</th><th>绑到哪一路</th><th>试一下</th></tr></thead>
      <tbody>${devs.map((d) => {
        const onTxt = d.on === true ? "开" : d.on === false ? "关" : "—";
        const chips = roles.map(([k, lab]) => `<button type="button" class="btn btn-xs ${bound[k] === d.id ? "btn-success" : "btn-ghost"}" data-bind="${k}" data-id="${esc(d.id)}">${lab}</button>`).join(" ");
        return `<tr>
          <td>${esc(d.name)}<div class="muted"><code>${esc(d.id)}</code>${d.model ? " · " + esc(d.model) : ""}</div></td>
          <td>${d.online ? '<span class="badge badge-success badge-sm">在线</span>' : '<span class="badge badge-error badge-outline badge-sm">离线</span>'} ${onTxt}</td>
          <td class="bindbar">${chips}</td>
          <td><span class="join">
            <button type="button" class="btn btn-xs join-item btn-primary" data-sw="${esc(d.id)}" data-on="1">开</button>
            <button type="button" class="btn btn-xs join-item btn-ghost" data-sw="${esc(d.id)}" data-on="0">关</button>
          </span></td>
        </tr>`;
      }).join("")}</tbody></table></div>`;
  };
  $("#ewsave").onclick = (e) => busy(e.currentTarget, async () => {
    await api("/api/settings", { method: "PUT", body: collect() });
    toast("账号已保存", "success", { id: "ew" });
  }, "ew");
  $("#ewtok").onclick = (e) => busy(e.currentTarget, async () => {
    toast("正在用 token 登录…", "info", { sticky: true, id: "ew" });
    const r = await api("/api/settings/ewelink/token", { method: "POST", body: { access_token: $("#etok").value } });
    renderDevices(r.devices || []);
    toast("Token 可用。下面点选绑定即可。", "success", { id: "ew" });
  }, "ew");
  $("#te").onclick = (e) => busy(e.currentTarget, async () => {
    toast("正在登录易微联…", "info", { sticky: true, id: "ew" });
    await api("/api/settings", { method: "PUT", body: collect() });
    const r = await api("/api/settings/test/ewelink", { method: "POST", body: {} });
    renderDevices(r.devices || []);
    toast("登录成功。点「仓内长开」这类按钮绑定，再点试开/试关。", "success", { id: "ew" });
  }, "ew");
  $("#elist").onclick = async (e) => {
    const bind = e.target.closest("[data-bind]");
    const sw = e.target.closest("[data-sw]");
    const act = bind || sw;
    if (!act) return;
    await busy(act, async () => {
      if (bind) {
        const map = { light: "el", box_always: "eba", box_print: "ebp", room: "ero" };
        const inputId = map[bind.dataset.bind];
        $("#" + inputId).value = bind.dataset.id;
        await api("/api/settings", { method: "PUT", body: collect() });
        const hold = $("#" + inputId).closest(".bindbar") || $("#" + inputId).closest("span");
        hold.innerHTML = `<input type="hidden" id="${inputId}" value="${esc(bind.dataset.id)}"><code class="text-xs">${esc(bind.dataset.id)}</code>
          <span class="join">
            <button type="button" class="btn btn-xs join-item btn-primary" data-sw="${esc(bind.dataset.id)}" data-on="1">试开</button>
            <button type="button" class="btn btn-xs join-item btn-ghost" data-sw="${esc(bind.dataset.id)}" data-on="0">试关</button>
          </span>`;
        toast("已绑定 " + bind.textContent.trim(), "success", { id: "ew" });
        $("#elist").querySelectorAll("[data-bind='" + bind.dataset.bind + "']").forEach((b) => {
          const on = b.dataset.id === bind.dataset.id;
          b.classList.toggle("btn-success", on);
          b.classList.toggle("btn-ghost", !on);
        });
        return;
      }
      if (sw) {
        await api("/api/ewelink/switch", { method: "POST", body: { id: sw.dataset.sw, on: sw.dataset.on === "1" } });
        toast((sw.dataset.on === "1" ? "已开" : "已关") + "，看设备有没有动", "success", { id: "ew" });
      }
    }, "ew");
  };
  $("#ebound").onclick = async (e) => {
    const sw = e.target.closest("[data-sw]");
    if (!sw) return;
    await busy(sw, async () => {
      await api("/api/ewelink/switch", { method: "POST", body: { id: sw.dataset.sw, on: sw.dataset.on === "1" } });
      toast(sw.dataset.on === "1" ? "已开" : "已关", "success", { id: "ew" });
    }, "ew");
  };
  $("#tz").onclick = (e) => busy(e.currentTarget, async () => {
    toast("正在测试萤石…", "info", { sticky: true, id: "ez" });
    await api("/api/settings", { method: "PUT", body: collect() });
    const d = describeStatus(await api("/api/settings/test/ezviz", { method: "POST", body: {} }));
    toast(d.t, d.k, { id: "ez" });
  }, "ez");
}

boot().catch((e) => { root.textContent = e.message; });

async function viewSpools() {
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

  window.showIntakeModal = () => {
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

  api("/api/spools/cloud/sync", { method: "POST" }).then(res => {
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
