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
function card(inner, extraCls = "") {
  return `<section class="card bg-base-100 shadow-sm border border-base-300 masonry-item ${extraCls}">${inner.includes("card-body") ? inner : `<div class="card-body p-4 sm:p-6">${inner}</div>`}</section>`;
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
      <div class="auth-brand">P</div>
      <h1 class="card-title justify-center">PandaSpool</h1>
      <p class="text-center muted text-sm mb-2 -mt-1">自托管拓竹打印中控</p>
      <form id="f" class="flex flex-col gap-2">
        ${field("用户名", `<input name="username" class="input input-bordered w-full" autocomplete="username">`)}
        ${field("密码", `<input name="password" type="password" class="input input-bordered w-full" autocomplete="current-password">`)}
        <p class="text-error" id="err"></p>
        <div class="card-actions"><button class="btn btn-primary w-full" type="submit">进入</button></div>
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

function ppIcon(name, cls = "pp-icon", size) {
  const icons = {
    home: `<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>`,
    printer: `<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect width="12" height="8" x="6" y="14"/>`,
    spool: `<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/><path d="M12 2a10 10 0 0 1 10 10"/>`,
    flask: `<path d="M10 2v7.31M14 2v7.31m4.44 10.35A2 2 0 0 1 16.66 22H7.34a2 2 0 0 1-1.78-2.34L8 10h8l2.44 9.66zM8.5 15h7"/>`,
    matrix: `<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>`,
    flame: `<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>`,
    leaf: `<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>`,
    cog: `<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>`,
    exit: `<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>`
  };
  const body = icons[name];
  if (!body) return "";
  let s = parseInt(size, 10);
  if (!s) {
    if (cls.includes("w-6") || cls.includes("h-6") || cls.includes("pp-icon-title")) s = 24;
    else if (cls.includes("w-5") || cls.includes("h-5") || cls.includes("pp-icon-card")) s = 20;
    else if (cls.includes("w-3.5") || cls.includes("h-3.5") || cls.includes("pp-icon-xs")) s = 14;
    else if (cls.includes("w-4") || cls.includes("h-4") || cls.includes("pp-icon-sm")) s = 16;
    else s = 18;
  }
  return `<svg class="pp-icon ${cls}" width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:${s}px;height:${s}px;max-width:${s}px;max-height:${s}px;flex-shrink:0;display:inline-block;vertical-align:middle;">${body}</svg>`;
}

function renderApp(me) {
  root.innerHTML = "";
  root.append(h(`<div class="shell bg-base-200 min-h-screen flex flex-col">
    <header class="topbar">
      <div class="topbar-inner">
        <!-- Mobile Nav Toggle -->
        <div class="dropdown nav-mobile">
          <div tabindex="0" role="button" class="btn btn-ghost btn-sm p-1" aria-label="打开导航菜单">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16" /></svg>
          </div>
          <ul tabindex="0" class="menu menu-sm dropdown-content mt-3 z-[50] p-2 shadow-xl bg-base-100 rounded-2xl w-56 border border-base-300">
            <li><a href="#/" data-p="/">${ppIcon("home")} 总览</a></li>
            <li><a href="#/machine" data-p="/machine">${ppIcon("printer")} 机台</a></li>
            <li><a href="#/spools" data-p="/spools">${ppIcon("spool")} 料盘</a></li>
            <li><a href="#/materials" data-p="/materials">${ppIcon("flask")} 耗材</a></li>
            <li><a href="#/stock" data-p="/stock">${ppIcon("matrix")} 盘点</a></li>
            <li><a href="#/compare" data-p="/compare">${ppIcon("flame")} 横评</a></li>
            <li><a href="#/air" data-p="/air">${ppIcon("leaf")} 空气</a></li>
            <li><a href="#/settings" data-p="/settings">${ppIcon("cog")} 设置</a></li>
          </ul>
        </div>
        
        <!-- Brand -->
        <div class="flex items-center gap-2.5 px-1 py-0.5 cursor-pointer select-none shrink-0" id="brand-wrap" onclick="location.hash='#/'">
          <div class="w-8 h-8 rounded-xl bg-primary/15 text-primary flex items-center justify-center font-black text-base shadow-sm border border-primary/20">
            🐼
          </div>
          <div class="flex flex-col">
            <span class="text-base font-bold tracking-tight text-base-content leading-none" id="brand">${esc(me.title || "PandaSpool")}</span>
            <span class="text-[9px] font-bold text-primary uppercase tracking-wider mt-0.5">Control Hub</span>
          </div>
        </div>
        
        <!-- Desktop Pill Nav -->
        <nav class="nav-desktop items-center gap-1 bg-base-100/70 p-1 rounded-full border border-base-content/5 shadow-inner">
          <a href="#/" data-p="/" class="nav-pill">${ppIcon("home")}<span>总览</span></a>
          <a href="#/machine" data-p="/machine" class="nav-pill">${ppIcon("printer")}<span>机台</span></a>
          <a href="#/spools" data-p="/spools" class="nav-pill">${ppIcon("spool")}<span>料盘</span></a>
          <a href="#/materials" data-p="/materials" class="nav-pill">${ppIcon("flask")}<span>耗材</span></a>
          <a href="#/stock" data-p="/stock" class="nav-pill">${ppIcon("matrix")}<span>盘点</span></a>
          <a href="#/compare" data-p="/compare" class="nav-pill">${ppIcon("flame")}<span>横评</span></a>
          <a href="#/air" data-p="/air" class="nav-pill">${ppIcon("leaf")}<span>空气</span></a>
          <a href="#/settings" data-p="/settings" class="nav-pill">${ppIcon("cog")}<span>设置</span></a>
        </nav>
        
        <div class="grow"></div>
        
        <!-- Right User / Theme Area -->
        <div class="flex items-center gap-2 shrink-0">
          ${themeBtn()}
          <div class="user-badge-desktop items-center gap-2 pl-2 border-l border-base-content/10">
            <div class="w-7 h-7 rounded-full bg-primary/20 text-primary font-bold text-xs flex items-center justify-center">
              P
            </div>
            <span class="text-xs font-semibold text-base-content/80">${esc(me.title || "PandaSpool")}</span>
          </div>
          <button class="btn btn-ghost btn-sm text-xs opacity-75 hover:opacity-100 gap-1" id="out" title="退出系统">
            ${ppIcon("exit")}<span>退出</span>
          </button>
        </div>
      </div>
    </header>
    
    <main class="page flex-1 w-full" id="page"></main>
    
    <!-- Modals -->
    <dialog id="modal-danger" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg text-error">操作确认</h3>
        <p class="py-4" id="modal-danger-msg">确定执行此操作吗？</p>
        <div class="modal-action">
          <form method="dialog"><button class="btn">取消</button></form>
          <button class="btn btn-error" id="modal-danger-confirm">确定执行</button>
        </div>
      </div>
    </dialog>

    <!-- 料盘重量修改弹窗 -->
    <dialog id="modal-spool-weight" class="modal">
      <div class="modal-box max-w-sm rounded-2xl">
        <h3 class="font-bold text-base text-base-content flex items-center gap-2">
          ${ppIcon("spool", "w-4 h-4 text-primary")}
          <span id="modal-weight-title">修改料盘净重</span>
        </h3>
        <p class="text-xs text-base-content/60 mt-1 mb-4" id="modal-weight-subtitle">调整料盘剩余重量并同步记录</p>
        
        <div class="form-control mb-4">
          <label class="label py-1"><span class="label-text text-xs text-base-content/70">剩余净重 (g)</span></label>
          <div class="join w-full">
            <input type="number" id="modal-weight-input" class="input input-bordered input-sm join-item w-full font-mono text-center font-bold text-base" min="0" max="2500" step="10">
            <span class="btn btn-sm btn-disabled join-item">g</span>
          </div>
          <input type="range" id="modal-weight-range" class="range range-primary range-sm mt-3" min="0" max="1000" step="10">
          <div class="w-full flex justify-between text-[10px] px-1 font-mono text-base-content/50 mt-1">
            <span>0g</span>
            <span>250g</span>
            <span>500g</span>
            <span>750g</span>
            <span>1000g</span>
          </div>
        </div>

        <div class="flex flex-wrap gap-1.5 mb-4">
          <button type="button" class="btn btn-xs btn-outline" onclick="window.setSpoolWeightPreset(1000)">1000g 满盘</button>
          <button type="button" class="btn btn-xs btn-outline" onclick="window.setSpoolWeightPreset(750)">750g</button>
          <button type="button" class="btn btn-xs btn-outline" onclick="window.setSpoolWeightPreset(500)">500g 半盘</button>
          <button type="button" class="btn btn-xs btn-outline" onclick="window.setSpoolWeightPreset(250)">250g</button>
          <button type="button" class="btn btn-xs btn-outline" onclick="window.setSpoolWeightPreset(0)">0g 空盘</button>
        </div>

        <div class="modal-action">
          <button type="button" class="btn btn-sm btn-ghost" onclick="document.getElementById('modal-spool-weight').close()">取消</button>
          <button type="button" class="btn btn-sm btn-primary" id="modal-weight-save">保存更新</button>
        </div>
      </div>
    </dialog>

  </div>`));
  $("#out").onclick = async () => { await api("/api/logout", { method: "POST", body: {} }); boot(); };
  root.addEventListener("click", (e) => {
    if (e.target.closest(".nav-mobile a")) {
      document.activeElement?.blur();
    }
  });
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

const AIR_FRESH_SECONDS = 15 * 60; // 统一 15 分钟阈值：15 分钟内视为在线/新鲜，超过视为离线/陈旧

function getProbeFreshness(ts) {
  let n = Number(ts);
  if (!n) {
    return { isOnline: false, isLive: false, label: "探头离线", badgeCls: "badge-ghost", textCls: "text-base-content/50", ageSec: null, ageText: "无采样记录" };
  }
  if (n > 1e12) n = Math.round(n / 1000);
  const now = Math.floor(Date.now() / 1000);
  const ageSec = Math.max(0, now - n);
  const ageText = airAgeText(n) || "刚刚";

  if (ageSec <= 300) {
    return { isOnline: true, isLive: true, label: "探头在线", badgeCls: "badge-success", textCls: "text-success", ageSec, ageText };
  }
  if (ageSec <= AIR_FRESH_SECONDS) {
    return { isOnline: true, isLive: false, label: `探头在线 · ${Math.floor(ageSec / 60)} 分钟前`, badgeCls: "badge-success", textCls: "text-success", ageSec, ageText };
  }
  return { isOnline: false, isLive: false, label: "探头离线 · 超过 15 分钟未更新", badgeCls: "badge-warning", textCls: "text-warning", ageSec, ageText };
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
  document.querySelectorAll(".nav-desktop a, .nav-mobile a").forEach((a) => {
    const on = route().startsWith(a.dataset.p) && (a.dataset.p !== "/" || route() === "/");
    a.classList.toggle("active", on);
    a.classList.toggle("menu-active", on);
  });
  $("#page")?.classList.remove("page-wide");
  const p = route();
  if (p !== "/machine") stopMachineLive();
  if (p !== "/air") stopAirLive();
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

function gcodeLabel(s) {
  const k = String(s || "").toUpperCase();
  const map = {
    RUNNING: "打印中", PRINTING: "打印中", PAUSE: "已暂停", PAUSED: "已暂停",
    SLICING: "切片中", PREPARE: "准备中", PREPARING: "准备中",
    FINISH: "已完成", FINISHED: "已完成", FAILED: "已失败", IDLE: "空闲",
  };
  return map[k] || (k || "空闲");
}
function isIdleGcode(s) {
  return ["IDLE", "FINISH", "FINISHED", "FAILED"].includes(String(s || "").toUpperCase());
}
function fmtTemp1(t) {
  const n = Number(t);
  if (t == null || Number.isNaN(n)) return "—";
  return String(Math.round(n * 10) / 10);
}
function fmtLocalMinute(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return String(iso).replace("T", " ").slice(0, 16);
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
function dedupeName(n) {
  const p = String(n || "").trim().split(/\s+/).filter(Boolean);
  return p.filter((t, i) => i === 0 || t !== p[i - 1]).join(" ");
}
function zoneLabel(z) {
  const k = String(z || "").toLowerCase();
  const map = { room: "房间", chamber: "仓内", enclosure: "仓内" };
  return map[k] || (z || "—");
}
// ===== Global Micro-Chart & Card Helpers (真实数据原则：无历史遥测时不伪造假曲线) =====
function sparklineSvg() { return ""; }
function sparkbarsSvg() { return ""; }

function statCard({
  icon = "",
  title,
  status = "",
  statusCls = "",
  val,
  valBadge = null,
  unit = "",
  sub = "",
  aux = [],
  meta = "",
  href = "",
  badge = "",
  active = false,
}) {
  let auxHtml = "";
  if (Array.isArray(aux) && aux.length > 0) {
    auxHtml = `
      <div class="pp-kpi-aux">
        ${aux.map(row => {
          if (Array.isArray(row)) {
            return `<div class="pp-kpi-aux-row"><span class="opacity-65">${esc(row[0])}</span><span class="font-medium">${esc(row[1])}</span></div>`;
          }
          return `<div class="pp-kpi-aux-row">${row}</div>`;
        }).join("")}
      </div>
    `;
  } else if (sub) {
    auxHtml = `<div class="pp-kpi-aux"><div class="pp-kpi-aux-row"><span class="truncate">${sub}</span></div></div>`;
  }

  let footerHtml = "";
  if (meta) {
    footerHtml = `<div class="pp-kpi-footer"><span class="truncate">${meta}</span></div>`;
  }

  const inner = `
    <div class="pp-kpi-card ${href ? 'cursor-pointer' : ''} ${active ? 'is-active' : ''}">
      <div>
        <div class="pp-kpi-header">
          <span class="pp-kpi-title">${icon ? `<span class="opacity-80 inline-flex items-center">${icon}</span>` : ""}<span>${esc(title)}</span></span>
          ${badge ? `<span class="badge badge-xs ${badge.cls || 'badge-ghost'} font-medium">${badge.text}</span>` : ""}
        </div>
        ${status ? `<div class="pp-kpi-status ${statusCls}">${esc(status)}</div>` : ""}
        <div class="pp-kpi-body">
          <span class="pp-kpi-value text-base-content">${esc(val)}${valBadge ? ` <span class="badge ${valBadge.cls || 'badge-warning badge-outline'} badge-xs font-normal align-middle">${esc(valBadge.text || valBadge)}</span>` : ""}</span>
          ${unit ? `<span class="pp-kpi-unit">${esc(unit)}</span>` : ""}
        </div>
      </div>
      <div>
        ${auxHtml}
        ${footerHtml}
      </div>
    </div>
  `;
  return href ? `<a href="${href}" class="block no-underline">${inner}</a>` : inner;
}


async function viewHome() {
  pageLoading("正在加载总览…");
  let d;
  try { d = await api("/api/summary"); }
  catch (ex) { pageError(ex); return; }
  const m = d.machine || {};
  const air = d.air || {};
  const mqtt = m.error && !m.connected
    ? `<span class="badge badge-error badge-outline badge-sm">${esc(m.error)}</span>`
    : m.connected
      ? `<span class="badge badge-success badge-sm">MQTT 已连接</span>`
      : `<a href="#/settings" class="badge badge-ghost hover:badge-primary cursor-pointer badge-sm">未连接拓竹，点击去设置</a>`;

  const printing = !!d.printing;
  const job = m.subtask || m.job || "";
  const remain = m.remaining != null && m.remaining !== "" ? m.remaining : "—";
  const boost = m.print_boost_active ? `<span class="badge badge-warning badge-sm">打印加强开着</span>` : "";
  const probe = getProbeFreshness(air.ts);
  const airAge = probe.ageText;
  const airStale = !probe.isOnline;
  const mgcode = String(m.gcode_state || "").toUpperCase();
  const mPrinting = printing && !isIdleGcode(mgcode);
  const mFinished = ["FINISH", "FINISHED"].includes(mgcode) || (!mPrinting && (Number(m.progress) === 100 || (m.print_ended_at && (Date.now() - new Date(m.print_ended_at).getTime() < 6 * 3600 * 1000))));
  const airPm = air.pm25;
  const todo = [];
  if ((d.drafts || 0) > 0) todo.push(`草稿 ${d.drafts} 条待确认`);
  if ((d.inbox || 0) > 0) todo.push(`收集箱 ${d.inbox} 张待处理`);

  $("#page").innerHTML = `
    <!-- 车间总览头部与设备连接状态 -->
    <div class="flex flex-wrap items-center justify-between gap-4 mb-6">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-base-content flex items-center gap-2">
          <span>车间总览</span>
          <span class="text-xs font-mono font-normal opacity-50">Workshop Telemetry</span>
        </h1>
        <p class="text-xs text-base-content/60 mt-1">拓竹 A1 打印工况与车间环境实时监测中枢</p>
      </div>
      <div class="flex flex-col items-end gap-1">
        <div class="text-xs text-base-content/60 font-medium font-mono" id="home-date-str"></div>
        <div class="text-2xl font-bold font-mono tracking-wider text-base-content" id="home-clock-str"></div>
        <div class="flex items-center gap-2 text-xs text-base-content/60">
          <span class="flex items-center gap-1.5">${m.connected ? '<span class="w-2 h-2 rounded-full bg-success inline-block"></span>拓竹已连接' : '<span class="w-2 h-2 rounded-full bg-error inline-block"></span>拓竹离线'}</span>
          <span>·</span>
          <span class="flex items-center gap-1.5">${probe.isOnline ? '<span class="w-2 h-2 rounded-full bg-success inline-block"></span>探头在线' : '<span class="w-2 h-2 rounded-full bg-warning inline-block"></span>探头离线'}</span>
        </div>
      </div>
    </div>

    <!-- 顶部 4 大 KPI 指标网格 -->
    <div class="pp-kpi-grid">
      ${statCard({
        icon: ppIcon("printer", "w-3.5 h-3.5"),
        title: "机台状态",
        status: mPrinting ? "任务打印中" : (mFinished ? "打印完成可取件" : (m.connected ? "设备待机就绪" : "机台离线")),
        statusCls: mPrinting ? "text-primary" : (mFinished ? "text-success" : (m.connected ? "text-base-content/80" : "text-error")),
        val: mPrinting ? (m.progress ?? 0) : (mFinished ? "100" : (m.connected ? "就绪" : "离线")),
        unit: (mPrinting || mFinished) ? "%" : "",
        aux: mPrinting ? [["打印耗时", `剩余约 ${m.remaining || "—"} 分钟`], ["活动任务", m.subtask || m.job || "打印中"]] : (mFinished ? [["热床状态", `${fmtTemp1(m.bed_temp)}°C · 已安全降温`], ["最近任务", m.subtask || m.job || "分盘任务已结束"]] : [["通讯协议", m.connected ? "MQTT 局域网在线" : "连接断开"], ["热床工况", `${fmtTemp1(m.bed_temp)}°C · 室温`]]),
        meta: mPrinting ? "拓竹 A1 高速打印中" : (mFinished ? "底板已降温，可随时安全取件" : "点击进入机台控制与视频监控"),
        href: "#/machine"
      })}
      ${statCard({
        icon: ppIcon("spool", "w-3.5 h-3.5"),
        title: "在机耗材",
        badge: { text: "当前料架", cls: "badge-ghost" },
        status: m.loaded_filament ? "已匹配云端条目" : "外部挂架在线",
        statusCls: m.loaded_filament ? "text-primary" : "text-base-content/80",
        val: esc(m.loaded_filament ? m.loaded_filament.split(" ")[0] : "外部料架"),
        unit: esc(m.loaded_filament ? m.loaded_filament.split(" ").slice(1).join(" ") : ""),
        aux: [["识别渠道", "Studio 预设反查"], ["供料方式", "外部挂架 (无 RFID)"]],
        meta: "拓竹 A1 外部料架支持直接进料",
        href: "#/spools"
      })}
      ${statCard({
        icon: ppIcon("matrix", "w-3.5 h-3.5"),
        title: "物理料盘台账",
        status: "拓竹云双向对齐",
        statusCls: "text-success",
        val: d.spools || (d.unopened + d.opened) || 0,
        unit: "盘",
        aux: [["已开封使用", `${d.opened || 0} 盘随时可用`], ["全新密封", `${d.unopened || 0} 盘备库`]],
        meta: "点击查看完整短编号 (PP-xxx) 资产",
        href: "#/spools"
      })}
      ${statCard({
        icon: ppIcon("leaf", "w-3.5 h-3.5"),
        title: "车间空气环境",
        badge: airPm != null ? (airPm <= 35 ? { text: "优", cls: "badge-success text-white" } : (airPm <= 75 ? { text: "工程关注", cls: "badge-warning" } : { text: "工程提醒", cls: "badge-error text-white" })) : { text: "离线", cls: "badge-ghost" },
        status: airPm != null ? (airPm <= 35 ? "浓度优良安全" : (airPm <= 75 ? "高于自定提醒值" : "颗粒物超标排风")) : "探头离线",
        statusCls: airPm != null ? (airPm <= 35 ? "text-success" : (airPm <= 75 ? "text-warning" : "text-error")) : "text-base-content/50",
        val: airPm != null ? airPm : "—",
        unit: airPm != null ? "µg/m³" : "",
        aux: [["温湿度", `${air.t_c != null ? `${air.t_c}℃` : "—"} · ${air.rh != null ? `${air.rh}%` : "—"}`], ["人员在场", air.presence ? "有人在场" : "无人静止"]],
        meta: air.ts ? `探头更新于 ${esc(airAge || "刚刚")}` : "等待 ESP32 遥测报文",
        href: "#/air"
      })}
    </div>

    <!-- 主控工况 8:4 双栏布局 -->
    <div class="pp-home-grid">
      <!-- 左栏：拓竹机台实时工况 (8 cols) -->
      <div class="flex flex-col gap-4">
        ${card(`
          <div class="flex flex-wrap items-center justify-between gap-2 border-b border-base-300/60 pb-3 mb-3">
            <h2 class="card-title text-base flex items-center gap-2">
              ${ppIcon("printer")}
              <span>拓竹机台实时工况</span>
            </h2>
            <div class="flex flex-wrap items-center gap-1.5">
              ${mqtt}
              ${boost}
            </div>
          </div>

          ${m.connected ? (() => {
            if (mPrinting) {
              return `
                <div class="mb-3">
                  <div class="text-xs text-base-content/50 font-medium">当前打印任务</div>
                  <div class="font-bold text-base sm:text-lg text-base-content flex items-center gap-1.5 truncate mt-0.5" title="${esc(job)}">
                    <span>📄</span> ${esc(job || "打印中")}
                  </div>
                  ${m.loaded_filament ? `<div class="text-xs text-primary font-medium mt-1 flex items-center gap-1"><span>🧵</span> 耗材：${esc(m.loaded_filament)}</div>` : ""}
                </div>

                <!-- 硬件渐变进度条 -->
                <div class="space-y-1.5 my-3 bg-base-200/50 p-3 rounded-xl border border-base-300/60">
                  <div class="flex justify-between text-xs font-semibold">
                    <span class="text-primary font-mono">${m.progress ?? 0}% 完成</span>
                    <span class="text-base-content/60 font-mono">预计剩余 ${esc(remain)} 分钟</span>
                  </div>
                  <div class="progress-hardware">
                    <div class="progress-hardware-fill" style="width: ${m.progress ?? 0}%"></div>
                  </div>
                </div>

                <!-- 4 宫格指标 -->
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 my-3">
                  <div class="metric-tile text-center flex flex-col justify-center py-2.5">
                    <div class="text-[11px] text-base-content/60 font-medium">热床温度</div>
                    <div class="metric-val-big text-primary my-1">${fmtTemp1(m.bed_temp)}<span class="metric-val-unit">°C</span></div>
                    <div class="text-[10px] text-base-content/50 font-mono">目标 ${fmtTemp1(m.bed_target)}°C</div>
                  </div>
                  <div class="metric-tile text-center flex flex-col justify-center py-2.5">
                    <div class="text-[11px] text-base-content/60 font-medium">喷嘴温度</div>
                    <div class="metric-val-big text-base-content my-1">${fmtTemp1(m.nozzle_temp)}<span class="metric-val-unit">°C</span></div>
                    <div class="text-[10px] text-base-content/50 font-mono">目标 ${fmtTemp1(m.nozzle_target)}°C</div>
                  </div>
                  <div class="metric-tile text-center flex flex-col justify-center py-2.5">
                    <div class="text-[11px] text-base-content/60 font-medium">打印层数</div>
                    <div class="metric-val-big text-base-content my-1">${m.layer ?? "—"}<span class="metric-val-unit">/${m.total_layer ?? "—"}</span></div>
                    <div class="text-[10px] text-base-content/50">当前进度</div>
                  </div>
                  <div class="metric-tile text-center flex flex-col justify-center py-2.5">
                    <div class="text-[11px] text-base-content/60 font-medium">预计剩余</div>
                    <div class="metric-val-big text-warning my-1">${esc(remain)}<span class="metric-val-unit">分</span></div>
                    <div class="text-[10px] text-base-content/50">倒计时</div>
                  </div>
                </div>
              `;
            }
            if (mFinished) {
              const bedN = Number(m.bed_temp);
              const isCooling = !isNaN(bedN) && bedN > 38;
              return `
                <div class="py-3.5 px-4 ${isCooling ? 'bg-warning/10 border-warning/30 text-warning' : 'bg-success/10 border-success/30 text-success'} border rounded-xl my-2">
                  <div class="flex items-center gap-2 font-bold text-sm">
                    ${isCooling ? '<span class="pulse-dot bg-warning"></span> 任务完成，热床仍在降温' : '<span>✓</span> 打印任务已完成'}
                  </div>
                  <p class="text-xs text-base-content/75 mt-1.5 leading-relaxed">${job ? `任务：${esc(job)} · ` : ""}${isCooling ? `热床当前 ${fmtTemp1(m.bed_temp)}°C，底板温度仍高，请等待自然冷却至室温后再取件，避免烫伤或底板形变。` : `热床已降温 (${fmtTemp1(m.bed_temp)}°C)，底板安全可取件。`}</p>
                </div>
                <div class="grid grid-cols-2 gap-3 my-3">
                  <div class="metric-tile text-center flex flex-col justify-center py-3">
                    <div class="text-[11px] text-base-content/60 font-medium">热床当前温度</div>
                    <div class="metric-val-big text-primary my-1">${fmtTemp1(m.bed_temp)}<span class="metric-val-unit">°C</span></div>
                    <div class="text-[10px] ${isCooling ? 'text-warning font-semibold' : 'text-base-content/50'}">${isCooling ? '自然降温中' : '已冷却至室温'}</div>
                  </div>
                  <div class="metric-tile text-center flex flex-col justify-center py-3">
                    <div class="text-[11px] text-base-content/60 font-medium">喷嘴当前温度</div>
                    <div class="metric-val-big text-base-content my-1">${fmtTemp1(m.nozzle_temp)}<span class="metric-val-unit">°C</span></div>
                    <div class="text-[10px] text-base-content/50">加热已停止</div>
                  </div>
                </div>
              `;
            }
            return `
              <div class="py-4 px-4 bg-base-200/50 rounded-xl my-2 border border-base-300/60">
                <div class="text-sm font-semibold flex items-center gap-2 text-base-content">
                  <span>💤</span> 设备待机就绪
                </div>
                <p class="text-xs text-base-content/60 mt-1">${job ? `上次任务：${esc(job)}` : "随时可开印新任务"}</p>
              </div>
              <div class="grid grid-cols-2 gap-3 my-3">
                <div class="metric-tile text-center flex flex-col justify-center py-3">
                  <div class="text-[11px] text-base-content/60 font-medium">热床温度</div>
                  <div class="metric-val-big text-primary my-1">${fmtTemp1(m.bed_temp)}<span class="metric-val-unit">°C</span></div>
                  <div class="text-[10px] text-base-content/50">待机室温</div>
                </div>
                <div class="metric-tile text-center flex flex-col justify-center py-3">
                  <div class="text-[11px] text-base-content/60 font-medium">喷嘴温度</div>
                  <div class="metric-val-big text-base-content my-1">${fmtTemp1(m.nozzle_temp)}<span class="metric-val-unit">°C</span></div>
                  <div class="text-[10px] text-base-content/50">加热未启动</div>
                </div>
              </div>
            `;
          })() : `
            <div class="py-8 text-center text-sm text-base-content/60 bg-base-200/40 rounded-xl my-2 border border-base-300/60">
              未连接拓竹打印机或 MQTT 离线，请在「设置」中填写拓竹账号并验证。
            </div>
          `}

          <div class="card-actions mt-3">
            <a class="btn btn-primary w-full gap-2 text-sm shadow-sm" href="#/machine">
              <span>进入机台控制与视频监控</span>
              <span>→</span>
            </a>
          </div>
        `)}
      </div>

      <!-- 右栏：车间环境微测点与待办 (4 cols) -->
      <div class="flex flex-col gap-4">
        ${card(`
          <div class="flex items-center justify-between border-b border-base-300/60 pb-3 mb-3">
            <h2 class="card-title text-base flex items-center gap-2">
              ${ppIcon("leaf")}
              <span>车间环境测点</span>
            </h2>
            <span class="text-xs font-mono ${probe.isOnline ? 'text-base-content/60' : 'text-warning'}">${air.ts ? `探头 ${esc(probe.ageText)}${!probe.isOnline ? ' · 离线' : ''}` : '离线'}</span>
          </div>

          ${air.ts ? `
            <div class="space-y-2.5 my-1">
              <div class="grid grid-cols-2 gap-2.5">
                <div class="metric-tile flex flex-col justify-between py-2.5 px-3">
                  <div class="text-[11px] text-base-content/60 font-medium">PM2.5 颗粒物</div>
                  <div class="metric-val-big ${airPm != null && airPm <= 35 ? 'text-success' : (airPm <= 75 ? 'text-warning' : 'text-error')} my-1">
                    ${air.pm25 ?? "—"}<span class="metric-val-unit">µg/m³</span>
                  </div>
                  <div class="text-[10px] text-base-content/50">${airPm != null ? (airPm <= 35 ? '优良安全' : (airPm <= 75 ? '高于提醒阈值' : '超标强化排风')) : '等待遥测'}</div>
                </div>
                <div class="metric-tile flex flex-col justify-between py-2.5 px-3">
                  <div class="text-[11px] text-base-content/60 font-medium">车间温湿度</div>
                  <div class="metric-val-big text-base-content my-1">
                    ${air.t_c ?? "—"}<span class="metric-val-unit">℃</span>
                  </div>
                  <div class="text-[10px] text-base-content/50 font-mono">相对湿度 ${air.rh ?? "—"}%</div>
                </div>
              </div>
              <div class="metric-tile flex items-center justify-between py-2 px-3">
                <div class="flex items-center gap-2 text-xs">
                  <span class="text-base-content/60 font-medium">微波在场:</span>
                  <span class="font-bold">${air.presence == null ? '<span class="text-base-content/40">未检测</span>' : (air.presence ? '<span class="text-success flex items-center gap-1.5"><span class="pulse-dot bg-success"></span>有人在场</span>' : '<span class="text-base-content/50">无人静止</span>')}</span>
                </div>
                <span class="text-[10px] font-mono text-base-content/40">毫米波多普勒</span>
              </div>
            </div>
          ` : `
            <div class="py-8 text-center text-sm text-base-content/60 bg-base-200/40 rounded-xl my-2 border border-base-300/60">
              尚未接入 ESP32 空气探头数据，接入后将自动展示温湿度与颗粒物指标。
            </div>
          `}

          <div class="card-actions mt-3 flex-wrap gap-2 pt-2 border-t border-base-300/40">
            <a class="btn btn-xs btn-ghost border border-base-content/10" href="#/air">空气时序曲线</a>
            <a class="btn btn-xs btn-ghost border border-base-content/10" href="#/stock">架子盘点</a>
            <a class="btn btn-xs btn-ghost border border-base-content/10" href="#/compare">参数横评</a>
          </div>
        `)}

        ${todo.length ? card(`
          <div class="flex items-center justify-between border-b border-base-300/60 pb-2 mb-2">
            <div class="flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-warning inline-block"></span>
              <h2 class="card-title text-xs font-semibold text-base-content/80">待办事项与质检</h2>
            </div>
            <span class="badge badge-ghost badge-xs text-[10px] opacity-70">${todo.length} 项</span>
          </div>
          <p class="text-xs font-medium text-base-content/85">${esc(todo.join(" · "))}</p>
          <p class="text-[11px] text-base-content/50 mt-1">去对应耗材产品页确认参数草稿、对齐实测与厂家资料。</p>
          <div class="card-actions mt-2.5">
            <a class="btn btn-xs btn-ghost border border-base-content/15 text-xs h-6 min-h-0" href="#/materials">前往处理 →</a>
          </div>
        `) : ""}
      </div>
    </div>
  `;

  const updateHomeClock = () => {
    const elClock = $("#home-clock-str");
    const elDate = $("#home-date-str");
    if (!elClock || !elDate) return;
    const now = new Date();
    const days = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
    elDate.innerText = `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 ${days[now.getDay()]}`;
    const pad = (n) => String(n).padStart(2, "0");
    elClock.innerText = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  };
  updateHomeClock();
  if (window.__homeClockTimer) clearInterval(window.__homeClockTimer);
  window.__homeClockTimer = setInterval(updateHomeClock, 1000);
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
    <div class="flex flex-wrap items-center justify-between gap-3 border-b border-base-300/60 pb-3 mb-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight mb-0.5 flex items-center gap-2">
          ${ppIcon("matrix", "w-6 h-6 text-primary")}
          <span>架子盘点矩阵 (色系 × 材料)</span>
        </h1>
        <p class="text-xs text-base-content/60">盘点口径：在架 ${m.total} 盘（未开封 + 开封），悬停或触控格子可细分规格属性。点击格子可快速筛选定位。</p>
      </div>
      <a href="#/materials" class="btn btn-sm btn-outline gap-1">
        ${ppIcon("flask")} <span>耗材目录</span>
      </a>
    </div>

    <!-- 顶部紧凑型 5 项统计条 -->
    <div class="pp-stat-bar">
      <div class="pp-stat-item">
        <div class="pp-stat-item-label">${ppIcon("matrix", "w-3.5 h-3.5")} 在架总盘数</div>
        <div class="pp-stat-item-val">${m.total} <span class="text-xs font-normal opacity-60">盘</span></div>
        <div class="pp-stat-item-sub">盘点实际存量</div>
      </div>
      <div class="pp-stat-item">
        <div class="pp-stat-item-label">${ppIcon("flame", "w-3.5 h-3.5 text-secondary")} PLA 族</div>
        <div class="pp-stat-item-val">${m.pla} <span class="text-xs font-normal opacity-60">盘</span></div>
        <div class="pp-stat-item-sub">普通/哑光/Lite/丝绸</div>
      </div>
      <div class="pp-stat-item">
        <div class="pp-stat-item-label">${ppIcon("flask", "w-3.5 h-3.5 text-info")} PETG 族</div>
        <div class="pp-stat-item-val">${m.petg} <span class="text-xs font-normal opacity-60">盘</span></div>
        <div class="pp-stat-item-sub">基础/HF/哑光</div>
      </div>
      <div class="pp-stat-item">
        <div class="pp-stat-item-label">${ppIcon("leaf", "w-3.5 h-3.5 text-success")} 哑光材质</div>
        <div class="pp-stat-item-val">${m.matte} <span class="text-xs font-normal opacity-60">盘</span></div>
        <div class="pp-stat-item-sub">PLA + PETG 哑光</div>
      </div>
      <div class="pp-stat-item">
        <div class="pp-stat-item-label">💰 在架均价</div>
        <div class="pp-stat-item-val">${buyAvg ? yuan(buyAvg) : "—"}</div>
        <div class="pp-stat-item-sub">${buyQty ? `已记 ${buyQty} 盘` : "暂无单价"}</div>
      </div>
    </div>
    ${card(`
      <h2 class="card-title text-base font-bold">色系 × 材料交叉矩阵</h2>
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
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 stk-bottom">
      <div class="card bg-base-100 p-4 rounded-2xl border border-base-300/80 shadow-sm flex flex-col justify-between">
        <div>
          <h2 class="font-bold text-sm mb-1 flex items-center gap-1.5"><span class="badge badge-warning badge-xs"></span>独苗色系</h2>
          <p class="text-xs text-base-content/50 mb-2">整架只有 1 盘的孤品色系</p>
        </div>
        <div class="text-sm font-medium leading-relaxed">${singleLine}</div>
      </div>
      <div class="card bg-base-100 p-4 rounded-2xl border border-base-300/80 shadow-sm flex flex-col">
        <h2 class="font-bold text-sm mb-1 flex items-center gap-1.5"><span class="badge badge-error badge-xs"></span>缺口分析</h2>
        <p class="text-xs text-base-content/50 mb-2">已有该色系/材质但对应格子为空</p>
        <ul class="stk-list max-h-48 overflow-y-auto text-xs space-y-1">${gapList}</ul>
      </div>
      <div class="card bg-base-100 p-4 rounded-2xl border border-base-300/80 shadow-sm flex flex-col">
        <h2 class="font-bold text-sm mb-1 flex items-center gap-1.5"><span class="badge badge-info badge-xs"></span>库存偏多</h2>
        <p class="text-xs text-base-content/50 mb-2">单格 ≥ 5 盘，可能可放缓囤货</p>
        <ul class="stk-list max-h-48 overflow-y-auto text-xs space-y-1">${extraList}</ul>
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
      <div class="inv-head flex flex-wrap items-center justify-between gap-3 mb-3">
        <div>
          <h1 class="card-title text-2xl font-bold mb-0.5">耗材目录与工况档案</h1>
          <p class="muted text-sm">管理耗材品牌、细分系列、打印工况参数与颜色。点击卡片可查看详情或上传包装贴纸由 AI 自动提取。</p>
        </div>
        <button type="button" class="btn btn-primary btn-sm gap-1" id="btn-open-create-material">
          <span>+</span> 录入新耗材
        </button>
      </div>
      <div class="inv-toolbar flex flex-wrap items-center gap-3">
        <input id="invq" class="input input-bordered input-sm inv-search flex-1 min-w-[200px]" placeholder="搜品牌 / 系列 / 材料 / 颜色">
        <select id="invbrand" class="select select-bordered select-sm">
          <option value="">全部品牌 (${brands.length})</option>
          ${brands.map((b) => `<option value="${esc(b)}">${esc(b)}</option>`).join("")}
        </select>
        <div class="join">
          <button type="button" class="btn btn-sm join-item" data-invf="shelf">在架耗材</button>
          <button type="button" class="btn btn-sm join-item" data-invf="all">全部档案</button>
        </div>
      </div>
    `)}
    <div id="invjump"></div>
    <div id="invsum" class="inv-sum muted text-sm my-2 font-medium"></div>
    <div id="list" class="inv-list"></div>

    <!-- 录入新耗材 Modal -->
    <dialog id="modal-create-mat" class="modal">
      <div class="modal-box max-w-lg">
        <h3 class="font-bold text-lg mb-3">📦 录入新耗材</h3>
        
        <div class="tabs tabs-boxed mb-4">
          <a class="tab tab-sm tab-active" id="tab-create-ai">✨ AI 拍图/截图建档 (推荐)</a>
          <a class="tab tab-sm" id="tab-create-manual">✍️ 手动快速建档</a>
        </div>

        <div id="pane-create-ai" class="space-y-3">
          <p class="text-xs muted">拍照或上传新耗材包装盒贴纸、TDS规格表或商品详情图，AI 视觉大模型将自动提取品牌、材料、工况温度并创建档案。</p>
          <div class="border-2 border-dashed border-base-300 rounded-box p-4 text-center">
            <input type="file" id="new-mat-file" class="file-input file-input-bordered file-input-sm w-full max-w-xs" accept="image/*">
            <p class="text-xs muted mt-2">支持 JPG、PNG、WebP，单张 ≤ 8MB</p>
          </div>
          <div class="modal-action">
            <button type="button" class="btn btn-ghost" onclick="$('#modal-create-mat').close()">取消</button>
            <button type="button" class="btn btn-primary" id="btn-do-ai-create">⚡ 开始 AI 建档</button>
          </div>
        </div>

        <div id="pane-create-manual" class="space-y-3 hidden">
          <form id="form-manual-create">
            <div class="row cols-2 mb-2">
              ${field("品牌", `<input id="new-m-brand" class="input input-bordered w-full" list="brand-list" placeholder="如：拓竹 / 大简 / 三绿" required>
                <datalist id="brand-list">${brands.map(b => `<option value="${esc(b)}"></option>`).join("")}</datalist>`)}
              ${field("材质大类", `<select id="new-m-mat" class="select select-bordered w-full" required>
                <option value="PLA">PLA</option>
                <option value="PETG">PETG</option>
                <option value="ABS">ABS</option>
                <option value="TPU">TPU</option>
                <option value="ASA">ASA</option>
                <option value="PC">PC</option>
                <option value="PA">PA (尼龙)</option>
                <option value="PETG-CF">PETG-CF</option>
                <option value="PLA-CF">PLA-CF</option>
              </select>`)}
            </div>
            ${field("细分系列 (选填)", inputEl("new-m-line", `placeholder="如：HF / 哑光 / 高速 / 碳纤"`))}
            ${field("备注说明 (选填)", inputEl("new-m-note", `placeholder="如：淘宝某店 / 体验装"`))}
            <div class="modal-action">
              <button type="button" class="btn btn-ghost" onclick="$('#modal-create-mat').close()">取消</button>
              <button type="submit" class="btn btn-primary">立即创建</button>
            </div>
          </form>
        </div>
      </div>
    </dialog>`;

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
      ? `在架 ${rows.length} 个耗材 · ${rolls} 卷未开封 · ${opened} 色有开封`
      : `全部耗材 ${rows.length} 个 · 其中在架 ${rows.filter((r) => r.s.shelf.length).length} 个`;
    if (!rows.length) {
      $("#list").innerHTML = card(`<p class="muted">${filter === "shelf" ? "架子是空的。切到「全部档案」查看，或点击右上角「+ 录入新耗材」。" : "没有匹配的耗材档案。"}</p>`);
      return;
    }
    $("#list").innerHTML = rows.map(({ p, s }) => {
      const colors = p.colors || [];
      return `
      <article class="inv-card card bg-base-100 shadow-sm hover:shadow-md transition border border-base-300/80 hover:border-primary/40 cursor-pointer p-4 rounded-2xl flex flex-col justify-between" data-id="${p.id}">
        <div>
          <div class="flex items-start justify-between gap-2">
            <div class="flex items-center gap-2.5">
              <div class="w-9 h-9 rounded-xl bg-primary/10 text-primary font-bold text-sm flex items-center justify-center border border-primary/15 shrink-0">
                ${esc((p.brand || "P").substring(0, 2))}
              </div>
              <div class="min-w-0">
                <h2 class="font-bold text-base text-base-content leading-tight truncate">
                  <span>${esc(p.brand)}</span>
                  <span class="text-primary font-semibold">${esc(p.product_line || "")}</span>
                </h2>
                <div class="text-[11px] text-base-content/50 mt-0.5">${colors.length} 种颜色登记</div>
              </div>
            </div>
            <span class="badge badge-neutral badge-sm font-semibold shrink-0">${esc(p.material)}</span>
          </div>

          <div class="inv-stats text-xs my-3 py-1.5 px-2.5 bg-base-200/50 rounded-xl flex items-center justify-between border border-base-300/50">
            <span><b class="text-primary font-mono font-bold">${s.unopened}</b> 卷未开封</span>
            <span><b class="text-warning font-mono font-bold">${s.opened}</b> 色开封</span>
            <span class="text-base-content/60">色卡 ${s.catalog}</span>
          </div>
        </div>

        <div>
          ${specStrip(p.card)}
          <div class="inv-chips mt-2.5 flex items-center gap-1.5 flex-wrap">
            ${s.shelf.length ? s.shelf.map(stockChip).join("") : `<span class="text-base-content/40 text-xs">架子上暂无存卷</span>`}
          </div>
        </div>
      </article>`;
    }).join("");
  };

  render();
  $("#invq").oninput = (e) => { query = e.target.value; render(); };
  $("#invbrand").onchange = (e) => { brand = e.target.value; render(); };

  $("#btn-open-create-material").onclick = () => {
    $("#modal-create-mat").showModal();
  };

  $("#tab-create-ai").onclick = () => {
    $("#tab-create-ai").classList.add("tab-active");
    $("#tab-create-manual").classList.remove("tab-active");
    $("#pane-create-ai").classList.remove("hidden");
    $("#pane-create-manual").classList.add("hidden");
  };

  $("#tab-create-manual").onclick = () => {
    $("#tab-create-manual").classList.add("tab-active");
    $("#tab-create-ai").classList.remove("tab-active");
    $("#pane-create-manual").classList.remove("hidden");
    $("#pane-create-ai").classList.add("hidden");
  };

  $("#btn-do-ai-create").onclick = async (e) => {
    const f = $("#new-mat-file")?.files?.[0];
    if (!f) { toast("请先选择或拍摄耗材图片", "warning"); return; }
    busy(e.currentTarget, async () => {
      toast("AI 正在解析图片并建档…", "info", { sticky: true, id: "ai-create" });
      const fd = new FormData();
      fd.append("file", f);
      const res = await fetch("/api/products/ai-create", { method: "POST", credentials: "include", body: fd }).then(r => r.json()).catch(() => ({}));
      if (!res.ok) {
        if (res.error === "not_configured") {
          toast(res.hint || "未配置 Vision Key，请先前往「设置」配置", "warning", { id: "ai-create", duration: 8000 });
        } else {
          toast(res.hint || res.error || "建档失败", "error", { id: "ai-create" });
        }
        return;
      }
      toast(res.hint || "耗材档案已建立！", "success", { id: "ai-create" });
      $("#modal-create-mat").close();
      location.hash = "#/materials/" + res.product_id;
    });
  };

  $("#form-manual-create").onsubmit = async (e) => {
    e.preventDefault();
    const brand = $("#new-m-brand").value.trim();
    const material = $("#new-m-mat").value.trim();
    const product_line = $("#new-m-line").value.trim();
    const notes = $("#new-m-note").value.trim();
    if (!brand || !material) { toast("品牌和材质必填", "warning"); return; }
    try {
      const p = await api("/api/products", { method: "POST", body: { brand, material, product_line, notes } });
      toast("耗材档案已创建", "success");
      $("#modal-create-mat").close();
      location.hash = "#/materials/" + p.id;
    } catch (ex) {
      toast("创建失败: " + ex.message, "error");
    }
  };

  $("#page").onclick = (e) => {
    const f = e.target.closest("[data-invf]");
    if (f) {
      filter = f.dataset.invf;
      sessionStorage.setItem("pp-inv-filter", filter);
      render();
      return;
    }
    const c = e.target.closest("[data-id]");
    if (c && !e.target.closest("details") && !e.target.closest("button") && !e.target.closest("dialog")) location.hash = "#/materials/" + c.dataset.id;
  };
}

async function viewProduct(id) {
  pageLoading("正在加载耗材档案…");
  let p, allClaims, spoolRecords;
  try {
    [p, allClaims, spoolRecords] = await Promise.all([
      api("/api/products/" + id),
      api("/api/claims?product_id=" + id),
      api("/api/spools"),
    ]);
  } catch (ex) { pageError(ex); return; }

  // 1. 提取工况参数
  const claims = (allClaims || []).filter(c => c.status === "confirmed" || !c.status);
  const getClaim = (k) => {
    const c = claims.find(x => x.key === k && !x.color_id && x.source !== "Studio");
    return c ? c.value : "";
  };
  const nozzleRange = getClaim("喷嘴温度范围");
  const nozzleRec = getClaim("喷嘴推荐温度");
  const bedRange = getClaim("热床温度范围");
  const bedRec = getClaim("热床推荐温度");
  const dryTemp = getClaim("烘干温度范围") || getClaim("烘干温度");
  const dryTime = getClaim("烘干时间");
  const speedMax = getClaim("打印速度上限") || getClaim("打印速度");
  const density = getClaim("密度");

  // 2. 物理料盘匹配
  const productSpools = (spoolRecords || []).filter(sp => (p.colors || []).some(c => c.id === sp.color_id));

  // 3. 关联拓竹云端规格：异步拉取标记物供编辑弹窗使用
  let bambuSpecs = [];
  api("/api/spools/cloud/sync", { method: "POST" }).then(res => {
    bambuSpecs = res.specs || [];
    const sel = $("#modal-bambu-spec");
    if (sel) {
      sel.innerHTML = `<option value="">-- 未关联云端规格 --</option>` + bambuSpecs.map(sp =>
        `<option value="${sp.cloud_id}" ${sp.cloud_id.toString() === (p.bambu_preset_id || "") ? "selected" : ""}>${esc(sp.name)}（${esc(sp.filament_id)} · ${esc(sp.vendor || "?")}）</option>`).join("");
    }
  }).catch(() => {});

  // 4. 颜色与图片凭据
  const colors = p.colors || [];
  const inbox = p.inbox || [];

  $("#page").innerHTML = `
    <!-- 顶部面包屑与标题操作栏 -->
    <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
      <div class="flex flex-wrap items-center gap-2">
        <a href="#/materials" class="btn btn-sm btn-ghost gap-1">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/></svg>
          耗材列表
        </a>
        <h1 class="text-2xl font-bold flex items-center gap-2">
          <span>${esc(p.brand)}</span>
          <span class="text-primary">${esc(p.product_line || "基础通用")}</span>
        </h1>
        <span class="badge badge-neutral font-bold">${esc(p.material)}</span>
        ${p.bambu_preset_id ? `<span class="badge badge-info badge-sm">已绑拓竹云端预设</span>` : `<span class="badge badge-ghost badge-sm text-xs">未绑拓竹预设</span>`}
      </div>
      <div class="flex items-center gap-2">
        <button type="button" class="btn btn-sm btn-primary gap-1" id="btn-show-ai">
          <span>📸</span> AI 识图录入
        </button>
        <button type="button" class="btn btn-sm btn-outline gap-1" id="btn-open-edit">
          <span>✏️</span> 编辑信息与工况
        </button>
        <button type="button" class="btn btn-sm btn-ghost text-error" id="delp" title="删除该耗材档案">
          删除
        </button>
      </div>
    </div>

    <!-- AI 识图填报 Hero 区域 -->
    <div class="card bg-base-100 shadow border border-primary/20 mb-6" id="ai-vision-box">
      <div class="card-body p-4 sm:p-5">
        <div class="flex flex-wrap items-center justify-between gap-2 border-b pb-2">
          <div>
            <h2 class="card-title text-base flex items-center gap-1.5">
              <span>✨ 耗材包装 / TDS 规格表 AI 自动识图写入</span>
              <span class="badge badge-primary badge-sm">免手写</span>
            </h2>
            <p class="text-xs muted mt-0.5">上传耗材包装盒、标签贴纸或 TDS 参数图，AI 视觉大模型将自动提取并填入喷嘴/热床/烘干/速度等工艺参数，无需繁琐手填。</p>
          </div>
          <span class="text-xs text-secondary font-medium">支持拖拽 / 粘贴 / 拍照</span>
        </div>
        <div class="mt-3 flex flex-col sm:flex-row items-center gap-3">
          <input type="file" id="ai-img-file" class="file-input file-input-bordered file-input-sm w-full max-w-sm" accept="image/*">
          <button type="button" class="btn btn-sm btn-primary whitespace-nowrap" id="btn-do-ai">
            <span>⚡ 开始识别并写入</span>
          </button>
          <span id="ai-run-hint" class="text-xs text-info"></span>
        </div>
      </div>
    </div>

    <!-- 核心工况参数看板 -->
    <div class="card bg-base-100 shadow mb-6">
      <div class="card-body p-4 sm:p-6">
        <div class="flex items-center justify-between mb-3">
          <h2 class="card-title text-base sm:text-lg flex items-center gap-2">
            <span>🛠️ 核心打印工艺工况</span>
            ${specStrip(p.card)}
          </h2>
          <button type="button" class="btn btn-sm btn-ghost text-primary" id="btn-quick-edit-specs">
            ✏️ 修改工况
          </button>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
          <div class="metric-tile text-center">
            <div class="text-[11px] text-base-content/60 flex items-center justify-center gap-1">🌡️ 喷嘴温度</div>
            <div class="text-lg font-bold font-mono text-primary mt-1">${esc(nozzleRec ? nozzleRec + " °C" : (nozzleRange ? nozzleRange + " °C" : "—"))}</div>
            <div class="text-[11px] text-base-content/50 mt-0.5 truncate" title="范围">${nozzleRange ? `范围: ${esc(nozzleRange)}°C` : "未录入范围"}</div>
            <div class="mt-1 flex justify-center">${sparklineSvg([200, 205, 210, 215, 210, 212], { color: "#6366f1", width: 64, height: 16 })}</div>
          </div>

          <div class="metric-tile text-center">
            <div class="text-[11px] text-base-content/60 flex items-center justify-center gap-1">🛏️ 热床温度</div>
            <div class="text-lg font-bold font-mono text-primary mt-1">${esc(bedRec ? bedRec + " °C" : (bedRange ? bedRange + " °C" : "—"))}</div>
            <div class="text-[11px] text-base-content/50 mt-0.5 truncate" title="范围">${bedRange ? `范围: ${esc(bedRange)}°C` : "未录入范围"}</div>
            <div class="mt-1 flex justify-center">${sparklineSvg([50, 55, 60, 60, 60, 60], { color: "#8b5cf6", width: 64, height: 16 })}</div>
          </div>

          <div class="metric-tile text-center">
            <div class="text-[11px] text-base-content/60 flex items-center justify-center gap-1">💨 烘干工艺</div>
            <div class="text-lg font-bold font-mono text-base-content mt-1">${esc(dryTemp ? dryTemp + " °C" : "—")}</div>
            <div class="text-[11px] text-base-content/50 mt-0.5 truncate" title="时长">${dryTime ? `时长: ${esc(dryTime)}` : "未录入时长"}</div>
          </div>

          <div class="metric-tile text-center">
            <div class="text-[11px] text-base-content/60 flex items-center justify-center gap-1">⚡ 打印速度</div>
            <div class="text-lg font-bold font-mono text-base-content mt-1">${esc(speedMax ? speedMax + " mm/s" : "—")}</div>
            <div class="text-[11px] text-base-content/50 mt-0.5 truncate">推荐速度上限</div>
          </div>

          <div class="metric-tile text-center">
            <div class="text-[11px] text-base-content/60 flex items-center justify-center gap-1">⚖️ 材料密度</div>
            <div class="text-lg font-bold font-mono text-base-content mt-1">${esc(density ? density + " g/cm³" : "—")}</div>
            <div class="text-[11px] text-base-content/50 mt-0.5 truncate">体积重量换算</div>
          </div>

          <div class="metric-tile col-span-2 sm:col-span-1 flex flex-col justify-between">
            <div>
              <div class="text-[11px] text-base-content/60 flex items-center gap-1">📝 工艺备注</div>
              <div class="text-xs font-medium line-clamp-2 text-base-content/80 mt-1" title="${esc(p.notes || '')}">
                ${esc(p.notes || "暂无特殊备注")}
              </div>
            </div>
            <div class="text-[11px] text-primary mt-1.5 cursor-pointer hover:underline" id="link-edit-note">点击编辑备注 →</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 颜色规格与库存 -->
    <div class="card bg-base-100 shadow mb-6">
      <div class="card-body p-4 sm:p-6">
        <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
          <div class="flex items-center gap-2">
            <h2 class="card-title text-base sm:text-lg">🎨 颜色规格与库存</h2>
            <span class="badge badge-ghost">${colors.length} 个颜色</span>
          </div>
          <div class="flex items-center gap-2">
            <button type="button" class="btn btn-xs sm:btn-sm btn-primary" id="btn-open-add-color">+ 添加颜色</button>
            <button type="button" class="btn btn-xs sm:btn-sm btn-outline" id="btn-open-stockin">记一笔入库</button>
          </div>
        </div>

        ${colors.length ? `
          <div class="overflow-x-auto">
            <table class="table table-zebra table-sm">
              <thead>
                <tr>
                  <th>颜色</th>
                  <th>色系</th>
                  <th>未开封</th>
                  <th>已开封</th>
                  <th>成本均价</th>
                  <th class="text-right">操作</th>
                </tr>
              </thead>
              <tbody>
                ${[...colors].sort((a, b) => Number(colorOnShelf(b)) - Number(colorOnShelf(a)) || (b.unopened - a.unopened)).map(c => {
                  const [bg, isLight] = getDetailedColor(c.name, c.color_family);
                  const s = bg ? `style="background:${bg}; color:${isLight?'#000':'#fff'}"` : "";
                  const fbg = FAMILY_COLOR[c.color_family];
                  const fisLight = LIGHT_FAM.has(c.color_family);
                  const fs = fbg ? `style="background:${fbg}; color:${fisLight?'#000':'#fff'}"` : "";
                  return `
                    <tr class="${colorOnShelf(c) ? "" : "opacity-50"}">
                      <td>
                        <span class="badge badge-sm border-0 font-medium" ${s}>${esc(c.name)}</span>
                        ${colorOnShelf(c) ? "" : `<span class="badge badge-ghost badge-xs ml-1">仅色卡</span>`}
                      </td>
                      <td><span class="badge badge-xs border-0" ${fs}>${esc(c.color_family)}</span></td>
                      <td>
                        <div class="flex items-center gap-1">
                          <button class="btn btn-xs btn-ghost px-1" data-cdec-u="${c.id}">-</button>
                          <span class="font-mono font-bold w-6 text-center" id="span-u-${c.id}">${c.unopened}</span>
                          <button class="btn btn-xs btn-ghost px-1" data-cinc-u="${c.id}">+</button>
                        </div>
                      </td>
                      <td>
                        <button class="btn btn-xs ${c.opened ? "btn-info btn-outline" : "btn-ghost"}" data-tog-o="${c.id}">
                          ${c.opened ? "有 1 卷" : "无"}
                        </button>
                      </td>
                      <td class="text-xs muted">${c.avg_price ? `${yuan(c.avg_price)} <span class="text-[10px]">(${c.buy_qty}盘)</span>` : "—"}</td>
                      <td class="text-right">
                        <button class="btn btn-ghost btn-xs text-error" data-delc="${c.id}" title="删除该颜色">删</button>
                      </td>
                    </tr>
                  `;
                }).join("")}
              </tbody>
            </table>
          </div>
        ` : `
          <div class="py-6 text-center muted text-sm bg-base-200/50 rounded-box">
            暂无颜色记录，点击上方「+ 添加颜色」或「AI 识图」自动提取颜色。
          </div>
        `}

        <!-- 关联物理料盘（只读速览） -->
        ${productSpools.length ? `
          <div class="border-t mt-4 pt-3">
            <h3 class="text-xs font-bold muted mb-2 flex items-center gap-1">
              <span>🧲 在架/在机物理料盘 (${productSpools.length})</span>
            </h3>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
              ${productSpools.map(sp => {
                const c = (p.colors || []).find(c => c.id === sp.color_id);
                const hex = (sp.color_hex || "").toLowerCase();
                const sw = /^[0-9a-f]{6}$/.test(hex) ? `<span class="inline-block w-2.5 h-2.5 rounded-full mr-1 align-middle" style="background:#${hex}"></span>` : "";
                return `
                  <div class="p-2 rounded bg-base-200 text-xs flex items-center justify-between">
                    <div>
                      <span class="font-mono font-bold text-primary">${esc(sp.short_code)}</span>
                      <span class="muted ml-1">${sw}${esc(c ? c.name : (sp.bambu_filament_name || "—"))}</span>
                    </div>
                    <span class="font-mono">${sp.net_weight_g != null ? Math.round(sp.net_weight_g) + "g" : "—"}</span>
                  </div>
                `;
              }).join("")}
            </div>
          </div>
        ` : ""}
      </div>
    </div>

    <!-- 包装贴纸与凭据图库 -->
    <div class="card bg-base-100 shadow mb-6">
      <div class="card-body p-4 sm:p-5">
        <div class="flex items-center justify-between mb-2">
          <h2 class="card-title text-base flex items-center gap-2">
            <span>📷 包装贴纸与凭据图库</span>
            <span class="badge badge-ghost badge-sm">${inbox.length} 张</span>
          </h2>
          <span class="text-xs muted">点击图片预览大图，支持直接以图重跑 AI 识别</span>
        </div>
        ${inbox.length ? `
          <div class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3">
            ${inbox.map(it => `
              <div class="group relative rounded-box overflow-hidden border border-base-300 bg-base-200">
                <img src="${esc(it.url)}" class="w-full h-28 object-cover cursor-pointer hover:opacity-90 transition" data-view-img="${esc(it.url)}" alt="${esc(it.name)}">
                <div class="p-1.5 flex items-center justify-between text-[11px] bg-base-100">
                  <span class="truncate" title="${esc(it.name)}">${esc(it.name)}</span>
                  <div class="flex items-center gap-1">
                    <button type="button" class="btn btn-ghost btn-xs p-0.5 text-primary" data-ai-reparse="${it.id}" title="以这张图重跑 AI 提取">AI</button>
                    <button type="button" class="btn btn-ghost btn-xs p-0.5 text-error" data-ibx="${it.id}" title="删除该图片">✕</button>
                  </div>
                </div>
              </div>
            `).join("")}
          </div>
        ` : `
          <div class="py-4 text-center text-xs muted bg-base-200/50 rounded-box">
            暂无凭据图片。点击顶部「AI 识图录入」上传包装或规格表图片即可归档。
          </div>
        `}
      </div>
    </div>

    <!-- 编辑工况与信息 Modal -->
    <dialog id="modal-spec-edit" class="modal">
      <div class="modal-box max-w-2xl">
        <h3 class="font-bold text-lg mb-3">✏️ 编辑耗材基础信息与工况参数</h3>
        <form id="form-specs">
          <div class="row cols-2 mb-2">
            ${field("细分系列", inputEl("m-pl", `value="${esc(p.product_line || "")}" placeholder="如：HF / 哑光 / 高速 / 碳纤"`))}
            ${field("关联拓竹云端规格", `<select id="modal-bambu-spec" class="select select-bordered w-full">
              <option value="">${p.bambu_preset_id ? "已关联当前规格" : "-- 未关联云端规格 --"}</option>
            </select>`)}
          </div>
          <div class="row cols-2 mb-2">
            ${field("品牌 (只读)", inputEl("m-pb", `value="${esc(p.brand)}" readonly class="input input-bordered w-full bg-base-200"`))}
            ${field("材质 (只读)", inputEl("m-pm", `value="${esc(p.material)}" readonly class="input input-bordered w-full bg-base-200"`))}
          </div>
          <div class="divider text-xs muted my-2">工况温度与工艺</div>
          <div class="row cols-2 mb-2">
            ${field("喷嘴推荐温度 (°C)", inputEl("m-nozzle-rec", `value="${esc(nozzleRec)}" placeholder="如：240"`))}
            ${field("喷嘴温度范围 (°C)", inputEl("m-nozzle-range", `value="${esc(nozzleRange)}" placeholder="如：230-250"`))}
          </div>
          <div class="row cols-2 mb-2">
            ${field("热床推荐温度 (°C)", inputEl("m-bed-rec", `value="${esc(bedRec)}" placeholder="如：75"`))}
            ${field("热床温度范围 (°C)", inputEl("m-bed-range", `value="${esc(bedRange)}" placeholder="如：70-80"`))}
          </div>
          <div class="row cols-2 mb-2">
            ${field("烘干温度 (°C)", inputEl("m-dry-temp", `value="${esc(dryTemp)}" placeholder="如：65"`))}
            ${field("烘干时长", inputEl("m-dry-time", `value="${esc(dryTime)}" placeholder="如：6h 或 6小时"`))}
          </div>
          <div class="row cols-2 mb-2">
            ${field("推荐最高速度 (mm/s)", inputEl("m-speed-max", `value="${esc(speedMax)}" placeholder="如：250"`))}
            ${field("材料密度 (g/cm³)", inputEl("m-density", `value="${esc(density)}" placeholder="如：1.27"`))}
          </div>
          <div class="mb-3">
            ${field("工艺与实测备注", textareaEl("m-notes", p.notes || "", `placeholder="官方打印建议、流量比率或注意事项"`))}
          </div>
          <div class="modal-action">
            <button type="button" class="btn btn-ghost" onclick="$('#modal-spec-edit').close()">取消</button>
            <button type="submit" class="btn btn-primary" id="btn-save-specs">保存修改</button>
          </div>
        </form>
      </div>
    </dialog>

    <!-- 添加颜色 Modal -->
    <dialog id="modal-add-color" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-3">🎨 添加新颜色</h3>
        <div class="space-y-3">
          ${field("颜色名称", `<input id="ac-name" class="input input-bordered w-full" placeholder="如：哑光黑 / 暖白 / 荧光绿">`)}
          ${field("所属色系 (可空自动猜测)", `<input id="ac-family" class="input input-bordered w-full" list="ac-f-list" placeholder="留空会自动按颜色名匹配">
            <datalist id="ac-f-list"><option value="白色系"><option value="黑灰色系"><option value="蓝色系"><option value="绿色系"><option value="红粉色系"><option value="黄橙色系"><option value="棕米色系"><option value="紫色系"><option value="金属色系"><option value="透明/自然色系"><option value="多色/效果色系"><option value="未分类"></datalist>`)}
          <div class="row cols-2">
            ${field("未开封盘数", inputEl("ac-u", `type="number" min="0" value="0"`))}
            ${field("是否已有开封卷", selectEl("ac-o", `<option value="0">无</option><option value="1">有 1 卷</option>`))}
          </div>
        </div>
        <div class="modal-action">
          <button type="button" class="btn btn-ghost" onclick="$('#modal-add-color').close()">取消</button>
          <button type="button" class="btn btn-primary" id="btn-save-add-color">添加颜色</button>
        </div>
      </div>
    </dialog>

    <!-- 入库记账 Modal -->
    <dialog id="modal-stock-in" class="modal">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-3">📦 入库记账</h3>
        <div class="space-y-3">
          ${field("选择颜色", selectEl("msin-color", `<option value="">-- 选择颜色 --</option>` + colors.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join("")))}
          <div class="row cols-2">
            ${field("采购盘数", inputEl("msin-qty", `type="number" step="0.1" min="0.1" value="1"`))}
            ${field("单价 (元/盘)", inputEl("msin-price", `type="number" step="0.01" min="0" placeholder="28.5"`))}
          </div>
          ${field("采购备注", inputEl("msin-note", `placeholder="店铺 / 活动 / 批次"`))}
          <label class="label cursor-pointer justify-start gap-2 py-1">
            <input id="msin-apply" type="checkbox" class="checkbox checkbox-sm" checked>
            <span class="label-text">同时增加在库库存数量</span>
          </label>
        </div>
        <div class="modal-action">
          <button type="button" class="btn btn-ghost" onclick="$('#modal-stock-in').close()">取消</button>
          <button type="button" class="btn btn-primary" id="btn-save-stock-in">确认记账</button>
        </div>
      </div>
    </dialog>

    <!-- 图片预览 Modal -->
    <dialog id="modal-img-preview" class="modal">
      <div class="modal-box max-w-4xl p-2 bg-base-300">
        <img id="preview-img-target" src="" class="w-full max-h-[80vh] object-contain rounded">
        <div class="modal-action p-2">
          <button type="button" class="btn btn-sm btn-ghost" onclick="$('#modal-img-preview').close()">关闭</button>
        </div>
      </div>
    </dialog>
  `;

  // 1. AI 识图填报
  const doAI = async (file, inboxID = "") => {
    toast("AI 正在分析并提取工况参数…", "info", { sticky: true, id: "ai-vision" });
    try {
      let res;
      if (file) {
        const fd = new FormData();
        fd.append("file", file);
        const r = await fetch("/api/products/" + id + "/ai-vision", { method: "POST", credentials: "include", body: fd });
        res = await r.json();
      } else if (inboxID) {
        res = await api("/api/products/" + id + "/ai-vision", { method: "POST", body: { inbox_id: inboxID } });
      }
      if (!res.ok) {
        if (res.error === "not_configured") {
          toast(res.hint || "未配置 Vision Key", "warning", { id: "ai-vision", duration: 8000 });
        } else {
          toast(res.hint || res.error || "识别失败", "error", { id: "ai-vision" });
        }
        viewProduct(id);
        return;
      }
      toast(res.hint || "AI 识别成功，已自动写入！", "success", { id: "ai-vision" });
      viewProduct(id);
    } catch (e) {
      toast("AI 识别出错: " + e.message, "error", { id: "ai-vision" });
    }
  };

  $("#btn-do-ai").onclick = () => {
    const f = $("#ai-img-file")?.files?.[0];
    if (!f) { toast("请先选择图片", "warning"); return; }
    doAI(f);
  };

  $("#btn-show-ai").onclick = () => {
    const box = $("#ai-vision-box");
    if (box) {
      box.scrollIntoView({ behavior: "smooth" });
      $("#ai-img-file")?.click();
    }
  };

  // 2. 编辑工况与基础信息
  const openEditModal = () => {
    const modal = $("#modal-spec-edit");
    if (modal) modal.showModal();
  };
  $("#btn-open-edit").onclick = openEditModal;
  $("#btn-quick-edit-specs").onclick = openEditModal;
  if ($("#link-edit-note")) $("#link-edit-note").onclick = openEditModal;

  $("#form-specs").onsubmit = (e) => {
    e.preventDefault();
    busy($("#btn-save-specs"), async () => {
      const body = {
        product_line: $("#m-pl").value.trim(),
        bambu_preset_id: $("#modal-bambu-spec") ? $("#modal-bambu-spec").value : (p.bambu_preset_id || ""),
        notes: $("#m-notes").value.trim(),
        nozzle_rec: $("#m-nozzle-rec").value.trim(),
        nozzle_range: $("#m-nozzle-range").value.trim(),
        bed_rec: $("#m-bed-rec").value.trim(),
        bed_range: $("#m-bed-range").value.trim(),
        dry_temp: $("#m-dry-temp").value.trim(),
        dry_time: $("#m-dry-time").value.trim(),
        speed_max: $("#m-speed-max").value.trim(),
        density: $("#m-density").value.trim(),
      };
      await api("/api/products/" + id + "/specs", { method: "POST", body });
      toast("工况与信息已保存", "success");
      $("#modal-spec-edit").close();
      viewProduct(id);
    });
  };

  // 3. 删除产品
  $("#delp").onclick = () => {
    window.confirmDanger("确定删除该耗材档案及其所有颜色和记录？此操作不可逆。", async () => {
      await api("/api/products/" + id, { method: "DELETE" });
      toast("耗材档案已删除", "success");
      location.hash = "#/materials";
    });
  };

  // 4. 添加颜色
  $("#btn-open-add-color").onclick = () => $("#modal-add-color").showModal();
  $("#btn-save-add-color").onclick = (e) => busy(e.currentTarget, async () => {
    const name = $("#ac-name").value.trim();
    if (!name) { toast("请填写颜色名称", "warning"); return; }
    await api("/api/colors", {
      method: "POST",
      body: {
        product_id: id,
        name,
        color_family: $("#ac-family").value.trim(),
        unopened: Number($("#ac-u").value) || 0,
        opened: Number($("#ac-o").value) || 0,
      }
    });
    toast("颜色已添加", "success");
    $("#modal-add-color").close();
    viewProduct(id);
  });

  // 5. 记一笔入库
  $("#btn-open-stockin").onclick = () => $("#modal-stock-in").showModal();
  $("#btn-save-stock-in").onclick = (e) => busy(e.currentTarget, async () => {
    const color_id = $("#msin-color").value;
    const qty = Number($("#msin-qty").value);
    const unit_price = Number($("#msin-price").value);
    if (!color_id) { toast("请先选择颜色", "warning"); return; }
    if (!(qty > 0) || !(unit_price >= 0)) { toast("请填写合法的盘数和单价", "warning"); return; }
    await api("/api/stock-ins", {
      method: "POST",
      body: {
        color_id,
        qty,
        unit_price,
        note: $("#msin-note").value.trim(),
        apply: $("#msin-apply").checked,
      }
    });
    toast("入库记录已保存", "success");
    $("#modal-stock-in").close();
    viewProduct(id);
  });

  // 6. 快捷调整颜色库存 & 图片操作委托
  $("#page").onclick = async (e) => {
    const btn = e.target.closest("button") || e.target.closest("[data-view-img]");
    if (!btn) return;
    try {
      // 增减未开封
      if (btn.dataset.cincU) {
        const cid = btn.dataset.cincU;
        const row = colors.find(c => c.id === cid);
        if (!row) return;
        const nextU = Number(row.unopened || 0) + 1;
        await api("/api/colors", { method: "POST", body: { id: cid, product_id: id, name: row.name, color_family: row.color_family, unopened: nextU, opened: row.opened } });
        viewProduct(id);
      }
      if (btn.dataset.cdecU) {
        const cid = btn.dataset.cdecU;
        const row = colors.find(c => c.id === cid);
        if (!row) return;
        const nextU = Math.max(0, Number(row.unopened || 0) - 1);
        await api("/api/colors", { method: "POST", body: { id: cid, product_id: id, name: row.name, color_family: row.color_family, unopened: nextU, opened: row.opened } });
        viewProduct(id);
      }
      // 切换开封
      if (btn.dataset.togO) {
        const cid = btn.dataset.togO;
        const row = colors.find(c => c.id === cid);
        if (!row) return;
        const nextO = row.opened ? 0 : 1;
        await api("/api/colors", { method: "POST", body: { id: cid, product_id: id, name: row.name, color_family: row.color_family, unopened: row.unopened, opened: nextO } });
        viewProduct(id);
      }
      // 删除颜色
      if (btn.dataset.delc) {
        const cid = btn.dataset.delc;
        window.confirmDanger("确定删除该颜色及其库存账？不可逆。", async () => {
          await api("/api/colors?id=" + cid, { method: "DELETE" });
          toast("颜色已删除", "success");
          viewProduct(id);
        });
      }
      // 预览图片大图
      if (btn.dataset.viewImg) {
        $("#preview-img-target").src = btn.dataset.viewImg;
        $("#modal-img-preview").showModal();
      }
      // 以旧图重跑 AI 识别
      if (btn.dataset.aiReparse) {
        doAI(null, btn.dataset.aiReparse);
      }
      // 删除图片凭据
      if (btn.dataset.ibx) {
        const imgId = btn.dataset.ibx;
        window.confirmDanger("确定删除该凭据图片？", async () => {
          await api("/api/inbox/" + imgId, { method: "DELETE" });
          toast("凭据已删除", "success");
          viewProduct(id);
        });
      }
    } catch (err) {
      toast(err.message, "error");
    }
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
    <div class="flex flex-wrap items-center justify-between gap-3 border-b pb-3 mb-4">
      <div>
        <h1 class="text-2xl font-bold mb-0.5">⚖️ 工艺参数横向横评</h1>
        <p class="text-xs muted">对比各耗材官方规格表与实测工艺参数。若同一指标存在不同说法或多源冲突，系统自动标出。</p>
      </div>
      <a href="#/materials" class="btn btn-sm btn-outline gap-1">
        <span>📦</span> 管理耗材档案
      </a>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    ${keys.length === 0 ? card(`
      <div class="text-center py-8">
        <h2 class="card-title justify-center text-lg mb-2">还没有可横评的数据</h2>
        <p class="muted text-sm max-w-md mx-auto">这里只展示已在耗材详情页录入或 AI 识别确认过的参数条目；同一字段有多个来源或数值时会标成冲突并列展示。</p>
        <div class="card-actions justify-center mt-4"><a class="btn btn-sm btn-primary" href="#/materials">前往耗材页录入参数</a></div>
      </div>`
    ) : keys.map((k) => {
      const uniq = new Set(data[k].map((c) => c.value + "|" + c.unit));
      const hit = uniq.size > 1;
      return card(`
        <div class="flex items-center justify-between border-b pb-2 mb-2">
          <h2 class="card-title text-base font-bold flex items-center gap-1.5">
            <span>${esc(k)}</span>
            ${hit ? '<span class="badge badge-error badge-xs font-semibold">⚠️ 存在冲突</span>' : '<span class="badge badge-success badge-xs badge-outline">一致</span>'}
          </h2>
          <span class="text-xs muted font-mono">${data[k].length} 条对比</span>
        </div>
        <div class="overflow-x-auto rounded-lg border border-base-300"><table class="table table-zebra table-sm w-full">
          <thead><tr><th>耗材产品</th><th>来源</th><th>工艺值</th></tr></thead>
          <tbody>${data[k].map((c) => `<tr>
            <td class="font-medium">${esc(c.product)}</td>
            <td><span class="badge badge-ghost badge-xs">${esc(c.source)}</span></td>
            <td class="font-mono font-bold text-primary">${esc(c.value)} <span class="text-xs font-normal opacity-70">${esc(c.unit)}</span></td>
          </tr>`).join("")}</tbody>
        </table></div>
      `);
    }).join("")}
    </div>
  `;
}

function swRow(label, role, icon = "") {
  return `<div class="form-control mb-1.5 p-2 rounded-lg bg-base-200/40 border border-base-300">
    <label class="label cursor-pointer p-0 w-full flex justify-between items-center">
      <span class="label-text text-sm font-medium flex items-center gap-1.5">${icon ? `<span>${icon}</span>` : ""}<span>${label}</span></span>
      <input type="checkbox" class="toggle toggle-primary toggle-sm" data-t="${role}">
    </label>
  </div>`;
}

async function viewMachine() {
  if (!$("#mach")) pageLoading("正在连接机台…");
  const ensureShell = () => {
    if ($("#mach")) return;
    $("#page").innerHTML = `<div id="mach" class="space-y-5">
      <!-- 顶部通栏：机台工况主卡 -->
      <div id="mach-top-card"></div>

      <!-- 中层双栏：智能插座联动 + 空气探头 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
        ${card(`
          <div class="flex items-center justify-between border-b border-base-300/60 pb-3 mb-3">
            <h2 class="card-title text-base flex items-center gap-2">
              <span>⚡</span><span>智能插座与环境联动</span>
            </h2>
            <span class="badge badge-ghost badge-sm text-xs">易微联通道</span>
          </div>
          <div class="space-y-1">
            ${swRow("仓内净化器长开", "box_always", "🌀")}
            ${swRow("仓内打印加强风量", "box_print", "🚀")}
            ${swRow("车间有人联动", "room", "👤")}
          </div>
        `)}

        ${card(`
          <div class="flex items-center justify-between border-b border-base-300/60 pb-3 mb-3">
            <h2 class="card-title text-base flex items-center gap-2">
              <span>🌿</span><span>车间环境空气探头</span>
            </h2>
            <a href="#/air" class="text-xs text-primary hover:underline flex items-center gap-0.5">
              <span>历史趋势</span><span>→</span>
            </a>
          </div>
          <div id="mach-air"></div>
        `)}
      </div>

      <!-- 底层双栏：视频监控 + 补光控制 -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div class="lg:col-span-8">
          ${card(`
            <div class="flex items-center justify-between border-b border-base-300/60 pb-3 mb-3">
              <h2 class="card-title text-base flex items-center gap-2">
                <span>📹</span><span>萤石实时视频监控</span>
              </h2>
              <div class="flex items-center gap-2">
                <button type="button" class="btn btn-xs btn-primary gap-1" id="ez-play">▶ 播放视频</button>
                <button type="button" class="btn btn-xs btn-ghost border border-base-content/15 gap-1" id="ez-stop">■ 停止</button>
              </div>
            </div>
            <div id="ezviz" class="pp-video-stage border border-base-300/80 rounded-xl overflow-hidden shadow-inner flex flex-col items-center justify-center text-sm gap-2">
              <div class="flex items-center gap-2 px-3 py-1 rounded-full bg-base-100/10 border border-white/10 text-slate-300 text-xs font-mono">
                <span class="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
                <span>萤石实时视频流 · 监控就绪</span>
              </div>
              <button type="button" class="btn btn-sm btn-primary gap-2 mt-1 shadow-md" onclick="document.getElementById('ez-play')?.click()">
                <span>▶</span><span>开始监控视频推流</span>
              </button>
              <div class="text-[11px] text-slate-400">720P 低延迟 HLS/FLV · 默认待机节约带宽</div>
            </div>
          `)}
        </div>

        <div class="lg:col-span-4 flex flex-col gap-4">
          ${card(`
            <div class="flex items-center justify-between border-b border-base-300/60 pb-3 mb-3">
              <h2 class="card-title text-base flex items-center gap-2">
                <span>💡</span><span>补光与控制面板</span>
              </h2>
              <span class="badge badge-ghost badge-sm text-xs">机箱照明</span>
            </div>
            <div class="py-1">
              ${swRow("机箱顶部补光灯", "light", "💡")}
            </div>
            <!-- 增加设备控制与链路遥测密度，去除空洞感 -->
            <div class="p-3 bg-base-200/50 rounded-xl border border-base-300/60 text-xs space-y-2 mt-2">
              <div class="font-semibold text-base-content flex items-center justify-between">
                <span class="flex items-center gap-1"><span>📡</span><span>中枢通讯链路</span></span>
                <span class="badge badge-success badge-xs">在线</span>
              </div>
              <div class="grid grid-cols-2 gap-2 pt-1 border-t border-base-300/50 text-[11px]">
                <div>
                  <span class="text-base-content/50 block">拓竹局域链路:</span>
                  <span class="font-mono font-medium text-base-content/80">MQTT 8883 直连</span>
                </div>
                <div>
                  <span class="text-base-content/50 block">视频推流鉴权:</span>
                  <span class="font-mono font-medium text-base-content/80">萤石 OpenCloud</span>
                </div>
              </div>
            </div>
            <div class="p-3 bg-base-200/30 rounded-xl border border-base-300/40 text-[11px] text-base-content/60 space-y-1">
              <div class="font-medium text-base-content/75">• 首层排查：开启顶部补光灯可消除阴影。</div>
              <div class="font-medium text-base-content/75">• 延时说明：推流采用 FLV 低延时协议 (1~2秒)。</div>
            </div>
          `)}
        </div>
      </div>
    </div>`;

    $("#mach").onchange = async (e) => {
      const t = e.target.closest("[data-t]");
      if (!t) return;
      const role = t.dataset.t;
      const on = t.checked;
      t.disabled = true;
      try {
        await api("/api/actuators/" + role, { method: "POST", body: { on } });
        toast("已发送控制指令", "success", { id: "mach" });
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
    const boost = b.print_boost_active ? `<span class="badge badge-warning badge-sm">打印加强开着</span>` : "";
    let spdStr = "";
    if (b.spd_lvl != null && String(b.spd_lvl) !== "2") {
        const lvlMap = {"1": "静音 50%", "3": "狂暴 124%", "4": "荒野狂飙 166%"};
        spdStr = `<span class="badge badge-secondary badge-sm">${lvlMap[String(b.spd_lvl)] || "未知速度"}</span>`;
    }

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
        return `<span class="opacity-70 ml-2">预计 ${isNextDay ? "次日 " : ""}${pad(end.getHours())}:${pad(end.getMinutes())} 结束</span>`;
    };

    const gcode = String(b.gcode_state || "").toUpperCase();
    const isPrinting = printing && !isIdleGcode(gcode);
    const isFinished = ["FINISH", "FINISHED"].includes(gcode) || (!isPrinting && (Number(b.progress) === 100 || (b.print_ended_at && (Date.now() - new Date(b.print_ended_at).getTime() < 6 * 3600 * 1000))));
    const isPaused = ["PAUSE", "PAUSED"].includes(gcode);
    const isFailed = ["FAILED"].includes(gcode);

    let statTitle = "状态";
    let statDesc = "";
    if (isPrinting) {
      statTitle = "打印中";
      statDesc = `剩余 ${formatTime(b.remaining)}${calcEnd(b.remaining)}`;
    } else if (isFinished) {
      const bedN = Number(b.bed_temp);
      if (!isNaN(bedN) && bedN > 38) {
        statTitle = "任务完成";
        statDesc = `热床降温中 (${fmtTemp1(b.bed_temp)}°C) · 待降温后再取件`;
      } else {
        statTitle = "已完成";
        statDesc = "打印圆满结束，底板已降温";
      }
    } else if (isPaused) {
      statTitle = "已暂停";
      statDesc = `进度 ${b.progress ?? "—"}% · 剩余 ${formatTime(b.remaining)}`;
    } else if (isFailed) {
      statTitle = "异常中断";
      statDesc = "打印中止或发生故障";
    } else {
      statTitle = "待机就绪";
      statDesc = "设备就绪 · 随时可开印";
    }

    $("#mach-top-card").innerHTML = `
      <div class="card bg-base-100 shadow-sm border border-base-300/80 p-5">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-base-300/60 pb-3 mb-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center text-xl font-bold border border-primary/20">
              🖨️
            </div>
            <div>
              <h1 class="text-xl font-bold tracking-tight text-base-content flex items-center gap-2">
                <span>拓竹 Bambu Lab A1</span>
                <span class="badge badge-primary badge-outline badge-sm">A1 Series</span>
              </h1>
              <div class="flex items-center gap-2 text-xs text-base-content/60 mt-0.5">
                ${b.connected ? '<span class="text-success flex items-center gap-1"><span class="pulse-dot bg-success"></span>MQTT 已连接</span>' : '<span class="text-error flex items-center gap-1">○ 未连接</span>'}
                <span>·</span>
                <span>${statTitle}</span>
                ${b.print_boost_active ? '<span>·</span><span class="text-warning">打印加强开启</span>' : ''}
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            ${boost}
            ${spdStr}
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-12 gap-5 items-center">
          <!-- 任务信息与进度 (7 cols) -->
          <div class="md:col-span-7 space-y-3">
            <div>
              <div class="text-xs text-base-content/50 font-medium">当前打印任务</div>
              <div class="text-base sm:text-lg font-bold text-base-content truncate mt-0.5" title="${esc(b.subtask || b.job || '待机中')}">
                📄 ${esc(b.subtask || b.job || "无活动任务 · 设备就绪")}
              </div>
              ${b.loaded_filament ? `<div class="text-xs text-primary font-medium mt-1 flex items-center gap-1"><span>🧵</span> 耗材：${esc(b.loaded_filament)}</div>` : ''}
            </div>

            <div class="space-y-1.5 bg-base-200/50 p-3 rounded-xl border border-base-300/60">
              <div class="flex justify-between items-center text-xs font-semibold">
                <span class="text-primary font-mono">${b.progress ?? 0}% 完成</span>
                <span class="text-base-content/60 font-mono">${statDesc}</span>
              </div>
              <div class="progress-hardware">
                <div class="progress-hardware-fill" style="width: ${b.progress ?? 0}%"></div>
              </div>
              <div class="text-[11px] text-base-content/50 pt-1 flex items-center justify-between">
                <span>层数：${b.layer ?? "—"} / ${b.total_layer ?? "—"}</span>
                <span>速度模式：${spdStr || "标准 100%"}</span>
              </div>
            </div>
          </div>

          <!-- 双温工况卡片 (5 cols) -->
          <div class="md:col-span-5 grid grid-cols-2 gap-3">
            <div class="metric-tile text-center flex flex-col justify-center py-3">
              <div class="text-xs text-base-content/60 font-medium">喷嘴温度</div>
              <div class="metric-val-big text-base-content my-1">
                ${formatTemp(b.nozzle_temp)}<span class="metric-val-unit">°C</span>
              </div>
              <div class="text-[11px] text-base-content/50 font-mono">目标 ${formatTemp(b.nozzle_target)}°C</div>
            </div>

            <div class="metric-tile text-center flex flex-col justify-center py-3">
              <div class="text-xs text-base-content/60 font-medium">热床温度</div>
              <div class="metric-val-big text-primary my-1">
                ${formatTemp(b.bed_temp)}<span class="metric-val-unit">°C</span>
              </div>
              <div class="text-[11px] text-base-content/50 font-mono">目标 ${formatTemp(b.bed_target)}°C</div>
            </div>
          </div>
        </div>
      </div>
    `;

    let airTs = Number(air.ts);
    if (airTs > 1e12) airTs /= 1000;
    const stale = airTs ? (Date.now() / 1000 - airTs) > 15 * 60 : false;
    const airPm = air.pm25;
    $("#mach-air").innerHTML = `
      <div class="grid grid-cols-3 gap-2.5 my-1">
        <div class="metric-tile text-center flex flex-col justify-between py-2.5">
          <div class="text-[11px] text-base-content/60 font-medium">💨 PM2.5</div>
          <div class="metric-val-big ${airPm != null && airPm <= 35 ? 'text-success' : (airPm <= 75 ? 'text-warning' : 'text-error')} my-1">${air.pm25 ?? "—"}<span class="metric-val-unit">µg/m³</span></div>
          <div class="text-[10px] text-base-content/50">${airPm != null ? (airPm <= 35 ? '优良状态' : (airPm <= 75 ? '高于自定提醒值' : '颗粒物超标')) : '等待遥测'}</div>
        </div>
        <div class="metric-tile text-center flex flex-col justify-between py-2.5">
          <div class="text-[11px] text-base-content/60 font-medium">🌡️ 车间温湿度</div>
          <div class="metric-val-big text-base-content my-1">${air.t_c ?? "—"}<span class="metric-val-unit">℃</span></div>
          <div class="text-[10px] text-base-content/50 font-mono">相对湿度 ${air.rh ?? "—"}%</div>
        </div>
        <div class="metric-tile text-center flex flex-col justify-between py-2.5">
          <div class="text-[11px] text-base-content/60 font-medium">👤 毫米波雷达</div>
          <div class="my-1 py-0.5">${air.presence == null ? '<span class="text-base-content/40 text-lg font-bold">—</span>' : (air.presence ? '<span class="text-success text-sm sm:text-base font-bold flex items-center justify-center gap-1.5"><span class="pulse-dot bg-success"></span>有人在场</span>' : '<span class="text-base-content/50 text-sm font-bold">无人静止</span>')}</div>
          <div class="text-[10px] text-base-content/50 font-mono">动态感应</div>
        </div>
      </div>
      <div class="text-xs ${stale ? "text-warning" : "text-base-content/50"} mt-2 text-right">${air.ts ? `探头 ${esc(airAgeText(air.ts))}${stale ? " (超过 15 分钟未更新)" : ""}` : "暂无探头数据"}</div>
    `;

    if (d.ezviz?.configured && $("#ezviz")) {
      const playBtn = $("#ez-play");
      const stopBtn = $("#ez-stop");
      if (playBtn && !playBtn.onclick) {
        playBtn.onclick = async () => {
          if (window.__ez) return;
          try {
            playBtn.disabled = true;
            playBtn.textContent = "正在获取视频流...";
            const cam = await api("/api/camera");
            const ezvizDiv = document.getElementById("ezviz");
            const ezW = ezvizDiv.clientWidth;
            const rot = d.ezviz?.rotation || "0";
            const isPortrait = (rot === "90" || rot === "-90");
            
            const cropVals = (d.ezviz?.crop || "0,0,0,0").split(",").map(x => Number(x) || 0);
            const cT = Math.max(0, Math.min(99, cropVals[0]));
            const cB = Math.max(0, Math.min(99, cropVals[1]));
            const cL = Math.max(0, Math.min(99, cropVals[2]));
            const cR = Math.max(0, Math.min(99, cropVals[3]));
            const fW = 1 - (cL + cR) / 100;
            const fH = 1 - (cT + cB) / 100;
            
            const baseAspect = isPortrait ? 9/16 : 16/9;
            const cropAspect = baseAspect * (fW / fH);
            const displayH = Math.min(520, Math.round(ezW / cropAspect));
            
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
            
            playBtn.textContent = "▶ 播放中";
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
            $("#ezviz").innerHTML = `
              <div class="w-12 h-12 rounded-full bg-base-100 shadow-md flex items-center justify-center text-xl text-primary cursor-pointer hover:scale-105 transition-transform" onclick="document.getElementById('ez-play')?.click()">
                ▶
              </div>
              <div class="font-medium text-xs text-base-content/75">监控视频未播放</div>
              <div class="text-[11px] text-base-content/40">点击「播放视频」加载实时画面（HLS/FLV 低延时流）</div>
            `;
            $("#ezviz").style.height = "";
            if (playBtn) playBtn.textContent = "▶ 播放视频";
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

// ===== 空气看板（环境观察：四层结构 + ECharts）=====

function stopAirLive() {
  if (window.__airTimer) {
    clearInterval(window.__airTimer);
    window.__airTimer = null;
  }
  if (window.__airChart) {
    try { window.__airChart.dispose(); } catch {}
    window.__airChart = null;
  }
  if (window.__airCharts && Array.isArray(window.__airCharts)) {
    window.__airCharts.forEach((c) => {
      try {
        if (c && typeof c.dispose === "function" && !c.isDisposed()) {
          c.dispose();
        }
      } catch {}
    });
    window.__airCharts = [];
  }
  ["air-pm-chart", "air-tvoc-chart", "air-env-chart"].forEach((id) => {
    const el = document.getElementById(id);
    if (el && window.echarts && typeof window.echarts.dispose === "function") {
      try { window.echarts.dispose(el); } catch {}
    }
  });
}

function calculateRecentTrend(points, maxWindowSec = 1800, threshold = 3) {
  if (!points || points.length < 3) return { text: "平稳", detail: "近期样本不足", windowDesc: "近30分钟" };
  const lastTs = points[points.length - 1][0];
  const windowStart = lastTs - maxWindowSec * 1000;
  const recent = points.filter((p) => p[0] >= windowStart && p[1] != null);
  if (recent.length < 3) {
    return { text: "样本稀疏", detail: "近30分钟无密集样本", windowDesc: "近30分钟" };
  }
  const mid = Math.floor(recent.length / 2);
  const firstHalf = recent.slice(0, mid);
  const secondHalf = recent.slice(mid);
  const avg1 = firstHalf.reduce((a, b) => a + b[1], 0) / firstHalf.length;
  const avg2 = secondHalf.reduce((a, b) => a + b[1], 0) / secondHalf.length;
  const delta = avg2 - avg1;
  if (delta > threshold) {
    return { text: "上升", detail: `较半小时前 +${delta.toFixed(1)}`, windowDesc: "近30分钟" };
  }
  if (delta < -threshold) {
    return { text: "回落", detail: `较半小时前 -${Math.abs(delta).toFixed(1)}`, windowDesc: "近30分钟" };
  }
  return { text: "平稳", detail: `波动在 ±${threshold} 以内`, windowDesc: "近30分钟" };
}

function parseAirTelemetry(desk, rows) {
  const now = Math.floor(Date.now() / 1000);
  const air = desk.air || {};
  const mobile = desk.mobile || {};
  const bambu = desk.bambu || {};

  // 机台状态归一化
  const gcode = String(bambu.gcode_state || "").toUpperCase();
  const isPrinting = (gcode === "RUNNING" || gcode === "PREPARE" || (bambu.progress > 0 && bambu.progress < 100)) && !["IDLE", "FINISH", "FINISHED", "FAILED"].includes(gcode);
  let printerText = "拓竹 A1 待机就绪";
  let printerBadge = "badge-ghost";
  if (isPrinting) {
    printerText = `拓竹 A1 打印中 (${bambu.progress ?? 0}%)`;
    printerBadge = "badge-success text-white";
  } else if (gcode === "FINISH" || bambu.progress === 100) {
    printerText = "拓竹 A1 待机 (任务已完成)";
    printerBadge = "badge-ghost";
  } else if (gcode) {
    printerText = `拓竹 A1 ${gcodeLabel(gcode)}`;
  }
  const loadedFilament = bambu.loaded_filament || "";

  // 统一时长格式化与取整
  const formatAge = (sec) => {
    if (sec == null) return "无采样记录";
    if (sec < 60) return `${sec} 秒前`;
    if (sec < 3600) return `${Math.floor(sec / 60)} 分钟前`;
    return `${Math.floor(sec / 3600)} 小时前`;
  };

  // 1. 打印房间 A (Node A - PMS5003 + SHT31)
  const roomEntry = rows.find((r) => r.zone === "room" || !r.zone);
  const roomData = roomEntry?.data || air;
  const roomTs = roomEntry?.ts || air.ts;
  const roomFreshInfo = getProbeFreshness(roomTs);
  const roomAge = roomFreshInfo.ageSec;
  const roomFresh = roomFreshInfo.isLive;
  const roomOnline = roomFreshInfo.isOnline;
  const roomHasCache = roomOnline && !roomFresh;
  const roomHours = roomAge ? Math.max(1, Math.floor(roomAge / 3600)) : null;

  const pm25 = roomData.pm25 != null && !isNaN(Number(roomData.pm25)) ? Number(roomData.pm25) : null;
  const pm1 = roomData.pm1 ?? roomData.pm1_0;
  const pm10 = roomData.pm10;
  const room_t = roomData.t_c ?? roomData.temp;
  const room_rh = roomData.rh ?? roomData.humidity;
  const presence = roomData.presence === true || roomData.presence === 1 || roomData.human_occupied === true;

  let roomStatus = "等待采样";
  let roomStatusCls = "text-base-content/50";
  let roomDiffStr = "暂无对比";
  if (pm25 != null) {
    if (pm25 > 35) {
      roomStatus = "高于自定提醒值 (35)";
      roomStatusCls = "text-warning font-semibold";
      roomDiffStr = `提醒 35，高出 ${Math.round(pm25 - 35)} µg/m³`;
    } else {
      roomStatus = "低于自定提醒值 (35)";
      roomStatusCls = "text-base-content/80 font-medium";
      roomDiffStr = `提醒 35，距提醒线 ${Math.round(35 - pm25)} µg/m³`;
    }
  }

  // 2. 移动测点 B (Node B - S3 + ENS160 + AHT20)
  const mobEntry = rows.find((r) => r.zone === "mobile");
  const mobData = mobEntry?.data || mobile;
  const mobTs = mobEntry?.ts || mobile.ts;
  const mobAge = mobTs ? Math.max(0, now - mobTs) : null;
  const mobFresh = mobAge !== null && mobAge < 300; // 5分钟内视为新鲜
  const mobHours = mobAge ? Math.max(1, Math.floor(mobAge / 3600)) : null;

  const mobLocation = mobData.location || "工作台";
  const mob_tvoc_raw = mobData.tvoc != null && !isNaN(Number(mobData.tvoc)) ? Number(mobData.tvoc) : null;
  const mob_eco2 = mobData.eco2 != null ? Number(mobData.eco2) : null;
  const mob_aqi = mobData.aqi != null ? Number(mobData.aqi) : null;
  const mob_t = mobData.t_c ?? mobData.temp;
  const mob_rh = mobData.rh ?? mobData.humidity;

  let mobStatus = "等待读数";
  let mobStatusCls = "text-base-content/50";
  if (!mobFresh) {
    mobStatus = mobHours != null ? `未更新约 ${mobHours} 小时` : "未更新";
    mobStatusCls = "text-base-content/50 font-medium";
  } else if (mob_tvoc_raw != null) {
    if (mob_tvoc_raw > 220) {
      mobStatus = "高于自定提醒值 (220)";
      mobStatusCls = "text-warning font-semibold";
    } else {
      mobStatus = "低于自定提醒值 (220)";
      mobStatusCls = "text-base-content/80 font-medium";
    }
  }

  // 3. 打印仓内 A (Node A - ESP32-C3 探头)
  const ch_t = roomData.chamber_t_c ?? roomData.chamber_temp;
  const ch_rh = roomData.chamber_rh ?? roomData.chamber_humidity;
  const ch_tvoc = roomData.chamber_tvoc ?? roomData.tvoc;
  const ch_eco2 = roomData.chamber_eco2 ?? roomData.eco2;
  const exhaustOn = !!air.exhaust;

  let chamberStatus = ch_t != null ? `当前仓温 ${ch_t} ℃` : "等待读数";
  let chamberStatusCls = "text-base-content/80 font-medium";
  if (exhaustOn) {
    chamberStatus = "排风运行中";
    chamberStatusCls = "text-info font-semibold";
  } else if (ch_t != null && ch_t > 45) {
    chamberStatus = "高温预警 (>45℃)";
    chamberStatusCls = "text-warning font-semibold";
  }

  return {
    now,
    formatAge,
    printer: {
      text: printerText,
      badge: printerBadge,
      isPrinting,
      loadedFilament,
      gcode,
    },
    room: {
      name: "打印房间",
      node: "Node A",
      online: roomOnline,
      fresh: roomFresh,
      isOnline: roomOnline,
      hasCache: roomHasCache,
      ageSec: roomAge,
      ageStr: roomFreshInfo.ageText,
      hours: roomHours,
      ts: roomTs,
      status: roomStatus,
      statusCls: roomStatusCls,
      diffStr: roomDiffStr,
      pm25,
      pm1,
      pm10,
      t_c: room_t != null ? Number(room_t) : null,
      rh: room_rh != null ? Number(room_rh) : null,
      presence,
    },
    mobile: {
      name: "移动测点",
      node: "Node B",
      online: mobFresh,
      fresh: mobFresh,
      ageSec: mobAge,
      ageStr: formatAge(mobAge),
      hours: mobHours,
      ts: mobTs,
      location: mobLocation,
      status: mobStatus,
      statusCls: mobStatusCls,
      tvoc: mob_tvoc_raw,
      eco2: mob_eco2,
      aqi: mob_aqi,
      t_c: mob_t != null ? Number(mob_t) : null,
      rh: mob_rh != null ? Number(mob_rh) : null,
    },
    chamber: {
      name: "打印仓内",
      node: "Node A",
      online: roomFresh,
      fresh: roomFresh,
      hasCache: roomHasCache,
      ageSec: roomAge,
      ageStr: formatAge(roomAge),
      ts: roomTs,
      status: chamberStatus,
      statusCls: chamberStatusCls,
      t_c: ch_t != null ? Number(ch_t) : null,
      rh: ch_rh != null ? Number(ch_rh) : null,
      tvoc: ch_tvoc != null ? Number(ch_tvoc) : null,
      eco2: ch_eco2 != null ? Number(ch_eco2) : null,
      exhaustOn,
    },
  };
}

function prepareSeriesWithGaps(points, maxGapSec = 180) {
  if (!points || !points.length) return [];
  const sorted = points.slice().sort((a, b) => a[0] - b[0]);
  const out = [];
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i][0] - sorted[i - 1][0] > maxGapSec * 1000) {
      out.push([sorted[i - 1][0] + 1000, null]);
    }
    out.push(sorted[i]);
  }
  return out;
}

function extractPrintIntervals(asc, minMs, maxMs) {
  const rows = asc
    .filter((r) => r.ts * 1000 >= minMs - 300000 && r.ts * 1000 <= maxMs)
    .sort((a, b) => a.ts - b.ts);

  const intervals = [];
  let cur = null;

  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    const ts = r.ts * 1000;
    const isP = !!(r.data && r.data.printing);

    if (isP) {
      if (!cur) {
        cur = { start: ts, end: ts };
      } else {
        if (ts - cur.end <= 240 * 1000) {
          cur.end = ts;
        } else {
          if (cur.end > cur.start) intervals.push(cur);
          else intervals.push({ start: cur.start, end: cur.start + 60000 });
          cur = { start: ts, end: ts };
        }
      }
    } else {
      if (cur) {
        if (cur.end > cur.start) intervals.push(cur);
        else intervals.push({ start: cur.start, end: cur.start + 60000 });
        cur = null;
      }
    }
  }

  if (cur) {
    if (cur.end > cur.start) intervals.push(cur);
    else intervals.push({ start: cur.start, end: Math.min(maxMs, cur.start + 60000) });
  }

  return intervals
    .map((it) => ({
      start: Math.max(minMs, it.start),
      end: Math.min(maxMs, it.end),
    }))
    .filter((it) => it.end > it.start);
}

function extractPresenceIntervals(asc, minMs, maxMs) {
  // 只过滤房间测点 A 的上报，B 没有雷达传感器绝不能用来代表房间无人
  const rows = asc
    .filter((r) => (r.zone === "room" || !r.zone) && r.ts * 1000 >= minMs - 300000 && r.ts * 1000 <= maxMs)
    .sort((a, b) => a.ts - b.ts);

  const hasField = rows.some((r) => r.data && (r.data.presence !== undefined || r.data.human_occupied !== undefined));
  if (!hasField) {
    return { intervals: [], hasHistory: false };
  }

  const intervals = [];
  let cur = null;

  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    const ts = r.ts * 1000;
    const isPres = !!(r.data && (r.data.presence === true || r.data.presence === 1 || r.data.human_occupied === true));

    if (isPres) {
      if (!cur) {
        cur = { start: ts, end: ts };
      } else {
        if (ts - cur.end <= 240 * 1000) {
          cur.end = ts;
        } else {
          if (cur.end > cur.start) intervals.push(cur);
          else intervals.push({ start: cur.start, end: cur.start + 60000 });
          cur = { start: ts, end: ts };
        }
      }
    } else {
      if (cur) {
        if (cur.end > cur.start) intervals.push(cur);
        else intervals.push({ start: cur.start, end: cur.start + 60000 });
        cur = null;
      }
    }
  }

  if (cur) {
    if (cur.end > cur.start) intervals.push(cur);
    else intervals.push({ start: cur.start, end: Math.min(maxMs, cur.start + 60000) });
  }

  const clipped = intervals
    .map((it) => ({
      start: Math.max(minMs, it.start),
      end: Math.min(maxMs, it.end),
    }))
    .filter((it) => it.end > it.start);

  return { intervals: clipped, hasHistory: true };
}

function findPeak(points) {
  if (!points || !points.length) return null;
  let max = null;
  for (const p of points) {
    if (!p || p[1] == null || isNaN(p[1])) continue;
    if (!max || p[1] > max.val) {
      max = { ts: p[0], val: p[1] };
    }
  }
  return max;
}

function calculate30MinTrend(points, nowMs, isFresh, unit = "") {
  if (!isFresh) {
    return { text: "近 30 分钟无新样本", cls: "text-base-content/40", diffStr: "" };
  }
  if (!points || !points.length) {
    return { text: "近 30 分钟无新样本", cls: "text-base-content/40", diffStr: "无样本" };
  }
  const halfHourAgo = nowMs - 30 * 60 * 1000;
  const recent = points.filter((p) => p && p[1] != null && p[0] >= halfHourAgo);
  if (recent.length < 2) {
    return { text: "近 30 分钟无新样本", cls: "text-base-content/40", diffStr: "样本不足" };
  }
  const first = recent[0][1];
  const last = recent[recent.length - 1][1];
  const diff = Math.round((last - first) * 10) / 10;
  const absDiff = Math.abs(diff);

  if (absDiff < 0.5) {
    return { text: "平稳 ±0", cls: "text-base-content/70", diffStr: `波动 < 0.5 ${unit}` };
  }
  if (diff > 0) {
    return { text: `上升 +${diff} ${unit} ↑`, cls: "text-warning font-semibold", diffStr: `从 ${first} 升至 ${last}` };
  }
  return { text: `下降 ${diff} ${unit} ↓`, cls: "text-success font-semibold", diffStr: `从 ${first} 降至 ${last}` };
}

function formatTime(tsMs) {
  if (!tsMs) return "—";
  const d = new Date(tsMs);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

function formatAirXAxis(value, rangeMin) {
  const d = new Date(value);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  const timeStr = `${hh}:${mm}`;

  if (rangeMin > 720) {
    if (d.getHours() === 0 && d.getMinutes() === 0) {
      return `${d.getMonth() + 1}/${d.getDate()} 00:00`;
    }
  }
  return timeStr;
}

function buildAirTooltip(dark, printIntervals, presenceRes) {
  return {
    trigger: "axis",
    axisPointer: {
      type: "cross",
      label: { backgroundColor: dark ? "#333" : "#6a7985" },
    },
    formatter: function (params) {
      if (!params || !params.length) return "";
      const timeMs = params[0].value ? params[0].value[0] : params[0].axisValue;
      const d = new Date(timeMs);
      const hh = String(d.getHours()).padStart(2, "0");
      const mm = String(d.getMinutes()).padStart(2, "0");
      const ss = String(d.getSeconds()).padStart(2, "0");
      let html = `<div class="font-mono text-xs pb-1 mb-1 border-b border-base-content/10 font-bold">${hh}:${mm}:${ss}</div>`;

      // 提示背景事件
      const isP = printIntervals.some((it) => timeMs >= it.start && timeMs <= it.end);
      if (isP) {
        html += `<div class="text-[11px] text-emerald-500 font-semibold mb-0.5">● 打印区活动中 (A1)</div>`;
      }
      if (presenceRes && presenceRes.hasHistory) {
        const isPres = presenceRes.intervals.some((it) => timeMs >= it.start && timeMs <= it.end);
        if (isPres) {
          html += `<div class="text-[11px] text-blue-500 font-semibold mb-1">● 打印房间有人在场</div>`;
        }
      }

      params.forEach((p) => {
        if (p.value && p.value[1] != null) {
          const unit = p.seriesName.includes("温度") || p.seriesName.includes("仓温")
            ? "℃"
            : (p.seriesName.includes("湿度") ? "%" : (p.seriesName.includes("TVOC") ? "ppb" : "µg/m³"));
          html += `<div class="text-xs flex items-center justify-between gap-4">
            <span style="color:${p.color}">● ${p.seriesName}:</span>
            <b class="font-mono">${p.value[1]} ${unit}</b>
          </div>`;
        }
      });
      return html;
    },
  };
}

function buildPmChartOption(rangeMin, asc, dark, options = {}) {
  const txt = dark ? "#a0aec0" : "#4a5568";
  const split = dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)";
  const nowMs = Date.now();
  const minTime = nowMs - rangeMin * 60 * 1000;

  const printIntervals = extractPrintIntervals(asc, minTime, nowMs);
  const presenceRes = extractPresenceIntervals(asc, minTime, nowMs);

  const markAreaData = [];
  if (options.showBgPrint !== false && printIntervals.length > 0) {
    printIntervals.forEach((it) => {
      markAreaData.push([
        { name: "A1打印", xAxis: it.start, itemStyle: { color: "rgba(34, 197, 94, 0.12)" }, label: { show: false } },
        { xAxis: it.end },
      ]);
    });
  }
  if (options.showBgPresence !== false && presenceRes.hasHistory && presenceRes.intervals.length > 0) {
    presenceRes.intervals.forEach((it) => {
      markAreaData.push([
        { name: "有人活动", xAxis: it.start, itemStyle: { color: "rgba(59, 130, 246, 0.10)" }, label: { show: false } },
        { xAxis: it.end },
      ]);
    });
  }

  const pm25Points = asc
    .filter((r) => (r.zone === "room" || !r.zone) && r.data?.pm25 != null)
    .map((r) => [r.ts * 1000, Number(r.data.pm25)]);

  const pm1Points = asc
    .filter((r) => (r.zone === "room" || !r.zone) && (r.data?.pm1 != null || r.data?.pm1_0 != null))
    .map((r) => [r.ts * 1000, Number(r.data.pm1 ?? r.data.pm1_0)]);

  const pm10Points = asc
    .filter((r) => (r.zone === "room" || !r.zone) && r.data?.pm10 != null)
    .map((r) => [r.ts * 1000, Number(r.data.pm10)]);

  // 严格从有效真实样本取峰值
  const validPm25 = pm25Points.filter((p) => p && p[1] != null && p[0] >= minTime);
  const peakPm25 = findPeak(validPm25);

  const series = [
    {
      name: "PM2.5",
      type: "line",
      data: prepareSeriesWithGaps(pm25Points, 180),
      showSymbol: false,
      connectNulls: false,
      smooth: true,
      lineStyle: { width: 2.5, color: "#10b981" },
      itemStyle: { color: "#10b981" },
      markLine: {
        symbol: "none",
        silent: true,
        data: [{
          yAxis: 35,
          lineStyle: { color: "#f59e0b", type: "dashed", width: 1.5 },
          label: { position: "end", formatter: "提醒 35 µg/m³", color: "#f59e0b", fontSize: 11 },
        }],
      },
      markPoint: peakPm25 ? {
        data: [{ coord: [peakPm25.ts, peakPm25.val], value: peakPm25.val }],
        symbolSize: 32,
        itemStyle: { color: "#10b981" },
        label: { fontSize: 10, color: "#fff" },
      } : undefined,
      markArea: markAreaData.length > 0 ? {
        silent: true,
        data: markAreaData,
      } : undefined,
    },
  ];

  if (options.showPm1) {
    series.push({
      name: "PM1.0",
      type: "line",
      data: prepareSeriesWithGaps(pm1Points, 180),
      showSymbol: false,
      connectNulls: false,
      smooth: true,
      lineStyle: { width: 1.2, color: "#94a3b8" },
      itemStyle: { color: "#94a3b8" },
    });
  }

  if (options.showPm10) {
    series.push({
      name: "PM10",
      type: "line",
      data: prepareSeriesWithGaps(pm10Points, 180),
      showSymbol: false,
      connectNulls: false,
      smooth: true,
      lineStyle: { width: 1.2, color: "#f97316" },
      itemStyle: { color: "#f97316" },
    });
  }

  return {
    backgroundColor: "transparent",
    legend: { right: 16, top: 0, textStyle: { color: txt, fontSize: 12 }, icon: "round", itemWidth: 12, itemHeight: 4 },
    tooltip: buildAirTooltip(dark, printIntervals, presenceRes),
    // 严格统一绘图区宽度，左75px 右65px，保证三图上下时刻绝对对齐
    grid: [{ left: 75, right: 65, top: 25, bottom: 28, containLabel: false }],
    xAxis: [{
      type: "time",
      min: minTime,
      max: nowMs,
      axisLabel: { color: txt, hideOverlap: true, fontSize: 11, formatter: (val) => formatAirXAxis(val, rangeMin) },
      axisLine: { lineStyle: { color: split } },
      splitLine: { show: false },
    }],
    yAxis: [{
      type: "value",
      min: 0,
      position: "left",
      axisLabel: { color: txt, formatter: "{value} µg/m³", fontSize: 11 },
      splitLine: { lineStyle: { color: split } },
    }],
    series,
  };
}

function buildTvocChartOption(rangeMin, asc, dark, options = {}) {
  const txt = dark ? "#a0aec0" : "#4a5568";
  const split = dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)";
  const nowMs = Date.now();
  const minTime = nowMs - rangeMin * 60 * 1000;

  const printIntervals = extractPrintIntervals(asc, minTime, nowMs);
  const presenceRes = extractPresenceIntervals(asc, minTime, nowMs);

  const markAreaData = [];
  if (options.showBgPrint !== false && printIntervals.length > 0) {
    printIntervals.forEach((it) => {
      markAreaData.push([
        { name: "A1打印", xAxis: it.start, itemStyle: { color: "rgba(34, 197, 94, 0.12)" }, label: { show: false } },
        { xAxis: it.end },
      ]);
    });
  }
  if (options.showBgPresence !== false && presenceRes.hasHistory && presenceRes.intervals.length > 0) {
    presenceRes.intervals.forEach((it) => {
      markAreaData.push([
        { name: "有人活动", xAxis: it.start, itemStyle: { color: "rgba(59, 130, 246, 0.10)" }, label: { show: false } },
        { xAxis: it.end },
      ]);
    });
  }

  const chPoints = asc
    .filter((r) => (r.zone === "room" || !r.zone) && (r.data?.chamber_tvoc != null || r.data?.tvoc != null))
    .map((r) => [r.ts * 1000, Number(r.data.chamber_tvoc ?? r.data.tvoc)]);

  // 移动测点 B TVOC：严格断线切断，不跨地点串线
  const mobRows = asc.filter((r) => r.zone === "mobile" && r.data?.tvoc != null);
  const mobPoints = [];
  let lastLoc = null;
  for (const r of mobRows) {
    const loc = r.data?.location || "地点未指定";
    const tsMs = r.ts * 1000;
    if (lastLoc !== null && lastLoc !== loc) {
      mobPoints.push([tsMs - 1000, null]);
    }
    mobPoints.push([tsMs, Number(r.data.tvoc)]);
    lastLoc = loc;
  }

  const validCh = chPoints.filter((p) => p && p[1] != null && p[0] >= minTime);
  const peakCh = findPeak(validCh);

  const series = [
    {
      name: "打印仓内 TVOC (Node A)",
      type: "line",
      data: prepareSeriesWithGaps(chPoints, 180),
      showSymbol: false,
      connectNulls: false,
      smooth: true,
      lineStyle: { width: 2.2, color: "#a855f7" },
      itemStyle: { color: "#a855f7" },
      markLine: {
        symbol: "none",
        silent: true,
        data: [{
          yAxis: 220,
          lineStyle: { color: "#f43f5e", type: "dashed", width: 1.5 },
          label: { position: "end", formatter: "提醒 220 ppb", color: "#f43f5e", fontSize: 11 },
        }],
      },
      markPoint: peakCh ? {
        data: [{ coord: [peakCh.ts, peakCh.val], value: peakCh.val }],
        symbolSize: 32,
        itemStyle: { color: "#a855f7" },
        label: { fontSize: 10, color: "#fff" },
      } : undefined,
      markArea: markAreaData.length > 0 ? {
        silent: true,
        data: markAreaData,
      } : undefined,
    },
    {
      name: `移动测点 B TVOC (${options.mobLocation || "工作台"})`,
      type: "line",
      data: prepareSeriesWithGaps(mobPoints, 180),
      showSymbol: false,
      connectNulls: false,
      smooth: true,
      lineStyle: { width: 1.8, type: "dashed", color: "#06b6d4" },
      itemStyle: { color: "#06b6d4" },
    },
  ];

  return {
    backgroundColor: "transparent",
    legend: { right: 16, top: 0, textStyle: { color: txt, fontSize: 12 }, icon: "round", itemWidth: 12, itemHeight: 4 },
    tooltip: buildAirTooltip(dark, printIntervals, presenceRes),
    // 严格对齐左75px 右65px
    grid: [{ left: 75, right: 65, top: 25, bottom: 28, containLabel: false }],
    xAxis: [{
      type: "time",
      min: minTime,
      max: nowMs,
      axisLabel: { color: txt, hideOverlap: true, fontSize: 11, formatter: (val) => formatAirXAxis(val, rangeMin) },
      axisLine: { lineStyle: { color: split } },
      splitLine: { show: false },
    }],
    yAxis: [{
      type: "value",
      min: 0,
      position: "left",
      axisLabel: { color: txt, formatter: "{value} ppb", fontSize: 11 },
      splitLine: { lineStyle: { color: split } },
    }],
    series,
  };
}

function buildEnvChartOption(rangeMin, asc, dark, options = {}) {
  const txt = dark ? "#a0aec0" : "#4a5568";
  const split = dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)";
  const nowMs = Date.now();
  const minTime = nowMs - rangeMin * 60 * 1000;

  const printIntervals = extractPrintIntervals(asc, minTime, nowMs);
  const presenceRes = extractPresenceIntervals(asc, minTime, nowMs);

  const chTemp = asc
    .filter((r) => (r.zone === "room" || !r.zone) && r.data?.chamber_t_c != null)
    .map((r) => [r.ts * 1000, Number(r.data.chamber_t_c)]);
  const rmTemp = asc
    .filter((r) => (r.zone === "room" || !r.zone) && r.data?.t_c != null)
    .map((r) => [r.ts * 1000, Number(r.data.t_c)]);

  const chRh = asc
    .filter((r) => (r.zone === "room" || !r.zone) && r.data?.chamber_rh != null)
    .map((r) => [r.ts * 1000, Number(r.data.chamber_rh)]);
  const rmRh = asc
    .filter((r) => (r.zone === "room" || !r.zone) && r.data?.rh != null)
    .map((r) => [r.ts * 1000, Number(r.data.rh)]);

  const validChT = chTemp.filter((p) => p && p[1] != null && p[0] >= minTime);
  const peakChT = findPeak(validChT);

  const series = [
    {
      name: "仓内温度",
      type: "line",
      yAxisIndex: 0,
      data: prepareSeriesWithGaps(chTemp, 180),
      showSymbol: false,
      connectNulls: false,
      smooth: true,
      lineStyle: { width: 2.2, color: "#f59e0b", type: "solid" },
      itemStyle: { color: "#f59e0b" },
      markPoint: peakChT ? {
        data: [{ coord: [peakChT.ts, peakChT.val], value: peakChT.val }],
        symbolSize: 32,
        itemStyle: { color: "#f59e0b" },
        label: { fontSize: 10, color: "#fff" },
      } : undefined,
    },
    {
      name: "房间温度",
      type: "line",
      yAxisIndex: 0,
      data: prepareSeriesWithGaps(rmTemp, 180),
      showSymbol: false,
      connectNulls: false,
      smooth: true,
      lineStyle: { width: 1.5, color: "#ea580c", type: "solid" },
      itemStyle: { color: "#ea580c" },
    },
    {
      name: "仓内湿度",
      type: "line",
      yAxisIndex: 1,
      data: prepareSeriesWithGaps(chRh, 180),
      showSymbol: false,
      connectNulls: false,
      smooth: true,
      lineStyle: { width: 2, color: "#06b6d4", type: "dashed" },
      itemStyle: { color: "#06b6d4" },
    },
    {
      name: "房间湿度",
      type: "line",
      yAxisIndex: 1,
      data: prepareSeriesWithGaps(rmRh, 180),
      showSymbol: false,
      connectNulls: false,
      smooth: true,
      lineStyle: { width: 1.5, color: "#3b82f6", type: "dashed" },
      itemStyle: { color: "#3b82f6" },
    },
  ];

  return {
    backgroundColor: "transparent",
    legend: { right: 16, top: 0, textStyle: { color: txt, fontSize: 12 }, icon: "round", itemWidth: 12, itemHeight: 4 },
    tooltip: buildAirTooltip(dark, printIntervals, presenceRes),
    // 严格对齐左75px 右65px
    grid: [{ left: 75, right: 65, top: 25, bottom: 28, containLabel: false }],
    xAxis: [{
      type: "time",
      min: minTime,
      max: nowMs,
      axisLabel: { color: txt, hideOverlap: true, fontSize: 11, formatter: (val) => formatAirXAxis(val, rangeMin) },
      axisLine: { lineStyle: { color: split } },
      splitLine: { show: false },
    }],
    yAxis: [
      {
        type: "value",
        scale: true,
        position: "left",
        min: (value) => {
          const span = value.max - value.min;
          if (span < 2.0) {
            const mid = (value.max + value.min) / 2;
            return Math.floor((mid - 1.0) * 10) / 10;
          }
          return Math.floor((value.min - 0.5) * 10) / 10;
        },
        max: (value) => {
          const span = value.max - value.min;
          if (span < 2.0) {
            const mid = (value.max + value.min) / 2;
            return Math.ceil((mid + 1.0) * 10) / 10;
          }
          return Math.ceil((value.max + 0.5) * 10) / 10;
        },
        axisLabel: { color: txt, formatter: "{value} ℃", fontSize: 11 },
        splitLine: { lineStyle: { color: split } },
      },
      {
        type: "value",
        min: 0,
        max: 100,
        position: "right",
        axisLabel: { color: txt, formatter: "{value} %", fontSize: 11 },
        splitLine: { show: false },
      },
    ],
    series,
  };
}

async function viewAir() {
  pageLoading("正在同步环境观察遥测…");

  let range = Number(localStorage.getItem("pp-air-range")) || 360;
  let showPm1 = localStorage.getItem("pp-air-pm1") === "true";
  let showPm10 = localStorage.getItem("pp-air-pm10") === "true";
  let showBgPrint = localStorage.getItem("pp-air-bg-print") !== "false";
  let showBgPresence = localStorage.getItem("pp-air-bg-pres") !== "false";

  let rows = [];
  let desk = {};
  try {
    const [rData, dData] = await Promise.all([
      api("/api/air?limit=" + range).catch(() => []),
      api("/api/desk").catch(() => ({})),
    ]);
    rows = Array.isArray(rData) ? rData : [];
    desk = dData || {};
  } catch (ex) {
    pageError(ex);
    return;
  }

  const telem = parseAirTelemetry(desk, rows);
  const asc = rows.slice().reverse();

  if (window.__airCharts && Array.isArray(window.__airCharts)) {
    window.__airCharts.forEach((c) => { try { c.dispose(); } catch {} });
  }
  window.__airCharts = [];
  if (window.__airChart) {
    window.__airChart.dispose();
    window.__airChart = null;
  }

  const nowMs = Date.now();
  const minMs = nowMs - range * 60 * 1000;

  // 1. 打印房间 PM2.5 统计（仅当前对象、当前指标、选定时间窗）
  const roomPmPoints = asc
    .filter((r) => (r.zone === "room" || !r.zone) && r.data?.pm25 != null && r.ts * 1000 >= minMs)
    .map((r) => [r.ts * 1000, Number(r.data.pm25)]);
  const roomPmPeak = findPeak(roomPmPoints);
  const roomPmTrend = calculate30MinTrend(roomPmPoints, nowMs, telem.room.fresh, "µg/m³");
  const roomPmAvg = roomPmPoints.length ? Math.round(roomPmPoints.reduce((s, p) => s + p[1], 0) / roomPmPoints.length) : null;

  // 2. 移动测点 B TVOC 统计（仅当前对象、当前指标、选定时间窗）
  const mobTvocPoints = asc
    .filter((r) => r.zone === "mobile" && r.data?.tvoc != null && r.ts * 1000 >= minMs)
    .map((r) => [r.ts * 1000, Number(r.data.tvoc)]);
  const mobTvocPeak = findPeak(mobTvocPoints);
  const mobTvocTrend = calculate30MinTrend(mobTvocPoints, nowMs, telem.mobile.fresh, "ppb");
  const mobTvocAvg = mobTvocPoints.length ? Math.round(mobTvocPoints.reduce((s, p) => s + p[1], 0) / mobTvocPoints.length) : null;

  // 3. 打印仓内温度统计（仅当前对象、当前指标、选定时间窗）
  const chamberTempPoints = asc
    .filter((r) => (r.zone === "room" || !r.zone) && r.data?.chamber_t_c != null && r.ts * 1000 >= minMs)
    .map((r) => [r.ts * 1000, Number(r.data.chamber_t_c)]);
  const chamberTempPeak = findPeak(chamberTempPoints);
  const chamberTempTrend = calculate30MinTrend(chamberTempPoints, nowMs, telem.chamber.fresh, "℃");
  const chamberTempAvg = chamberTempPoints.length ? (chamberTempPoints.reduce((s, p) => s + p[1], 0) / chamberTempPoints.length).toFixed(1) : null;

  const chamberTvocPoints = asc
    .filter((r) => (r.zone === "room" || !r.zone) && (r.data?.chamber_tvoc != null || r.data?.tvoc != null) && r.ts * 1000 >= minMs)
    .map((r) => [r.ts * 1000, Number(r.data.chamber_tvoc ?? r.data.tvoc)]);
  const chamberTvocPeak = findPeak(chamberTvocPoints);

  // 顶层 Header
  const headerHtml = `
    <div class="flex flex-wrap justify-between items-center gap-3 border-b border-base-300/60 pb-3 mb-5">
      <div>
        <h1 class="text-2xl font-bold tracking-tight mb-0.5 flex items-center gap-2">
          ${ppIcon("wind", "w-6 h-6 text-primary")}
          <span>环境观察</span>
        </h1>
        <div class="flex items-center gap-2 mt-1">
          ${telem.room.isOnline 
            ? (telem.room.fresh 
                ? '<span class="badge badge-success badge-sm gap-1 font-medium">● 探头 A 在线</span>' 
                : `<span class="badge badge-success badge-sm gap-1 font-medium">● 探头 A 在线 · ${Math.floor(telem.room.ageSec / 60)} 分钟前</span>`)
            : `<span class="badge badge-warning badge-sm gap-1 font-medium">○ 探头 A 离线 · ${telem.room.ageStr}</span>`}
          ${telem.printer.isPrinting
            ? '<span class="badge badge-primary badge-sm gap-1 font-medium">● 打印机工作中</span>'
            : '<span class="badge badge-ghost badge-sm gap-1 font-medium">○ 打印机待机</span>'}
          ${telem.chamber.exhaustOn
            ? '<span class="badge badge-info badge-sm gap-1 font-medium">● 智能排风开</span>'
            : '<span class="badge badge-ghost badge-sm gap-1 font-medium">○ 智能排风关</span>'}
        </div>
      </div>
      <div class="flex items-center gap-1.5 bg-base-200/80 p-1 rounded-xl border border-base-300/60 shadow-sm" id="air-range-group">
        <button type="button" class="btn btn-xs ${range === 60 ? 'btn-primary shadow-xs' : 'btn-ghost'}" data-air-range="60">1 小时</button>
        <button type="button" class="btn btn-xs ${range === 360 ? 'btn-primary shadow-xs' : 'btn-ghost'}" data-air-range="360">6 小时</button>
        <button type="button" class="btn btn-xs ${range === 1440 ? 'btn-primary shadow-xs' : 'btn-ghost'}" data-air-range="1440">24 小时</button>
      </div>
    </div>
  `;

  // 观察对象一：打印房间 A (PMS5003 + SHT31)
  const roomCardHtml = statCard({
    icon: ppIcon("flask", "w-3.5 h-3.5 text-primary"),
    title: "打印房间 A",
    status: telem.room.status,
    statusCls: telem.room.statusCls,
    val: telem.room.pm25 != null ? telem.room.pm25 : "—",
    unit: "µg/m³ PM2.5",
    aux: [
      ["提醒差值", telem.room.diffStr],
      ["室温 / 湿度", telem.room.t_c != null ? `${telem.room.t_c} ℃ · ${telem.room.rh} %` : "—"],
      ["人员状态", telem.room.presence ? "有人活动" : "未检出人员"],
    ],
    meta: `最新采样：${telem.room.ageStr}`,
    badge: { text: "测点 A (PMS5003)", cls: "badge-primary badge-outline" },
  });

  // 观察对象二：移动测点 B (S3 + ENS160 + AHT20)
  const mobCardHtml = statCard({
    icon: ppIcon("wind", "w-3.5 h-3.5 text-secondary"),
    title: "移动测点 B",
    status: telem.mobile.status,
    statusCls: telem.mobile.statusCls,
    val: telem.mobile.tvoc != null ? telem.mobile.tvoc : "—",
    valBadge: !telem.mobile.fresh ? { text: "历史", cls: "badge-warning badge-outline" } : null,
    unit: "ppb TVOC",
    aux: [
      ["当前位置", esc(telem.mobile.location)],
      ["测点温湿", `${telem.mobile.t_c != null ? `${telem.mobile.t_c} ℃ · ${telem.mobile.rh} %` : "—"}${!telem.mobile.fresh ? " (历史)" : ""}`],
      ["数据状态", telem.mobile.fresh ? "实时在线采集中" : "移动端未更新 · 保留最后有效值"],
    ],
    meta: `最后采样：${telem.mobile.ageStr}`,
    badge: { text: "测点 B (便携S3)", cls: "badge-secondary badge-outline" },
  });

  // 观察对象三：打印仓内 A (ESP32-C3 仓内探头)
  const chamberCardHtml = statCard({
    icon: ppIcon("spool", "w-3.5 h-3.5 text-accent"),
    title: "打印仓内 A",
    status: telem.chamber.status,
    statusCls: telem.chamber.statusCls,
    val: telem.chamber.t_c != null ? telem.chamber.t_c : "—",
    unit: "℃ 仓温",
    aux: [
      ["仓内湿度", telem.chamber.rh != null ? `${telem.chamber.rh} %` : "—"],
      ["仓内 TVOC", telem.chamber.tvoc != null ? `${telem.chamber.tvoc} ppb` : "—"],
      ["关联机台", telem.printer.isPrinting ? "打印中 · Bambu A1" : "空闲待机"],
    ],
    meta: `最新采样：${telem.chamber.ageStr}`,
    badge: { text: "仓内探头 (C3)", cls: "badge-accent badge-outline" },
  });

  // 3 列紧凑指标汇总横条（同一标准：最新采样、区间峰值、近30分钟变化）
  const summaryStripHtml = `
    <div class="pp-air-summary-strip">
      <!-- 1. 打印房间 PM2.5 -->
      <div class="pp-air-summary-col">
        <div class="pp-air-summary-col-head">
          <span class="pp-air-summary-col-title">${ppIcon("flask", "w-3.5 h-3.5 text-primary")} 1. 打印房间 PM2.5</span>
          <span class="badge badge-xs ${telem.room.fresh ? 'badge-success badge-outline' : 'badge-warning badge-outline'}">${telem.room.fresh ? '实时' : '历史'}</span>
        </div>
        <div class="pp-air-summary-cells">
          <div class="pp-air-cell">
            <span class="pp-air-cell-label">最新采样</span>
            <span class="pp-air-cell-val font-mono ${telem.room.pm25 && telem.room.pm25 > 35 ? 'text-warning' : 'text-success'}">${telem.room.pm25 != null ? telem.room.pm25 : '—'} <span class="text-xs font-normal text-base-content/60">µg/m³</span></span>
            <span class="pp-air-cell-sub">${telem.room.ageStr} · ${telem.room.fresh ? '实时' : '历史'}</span>
          </div>
          <div class="pp-air-cell">
            <span class="pp-air-cell-label">区间峰值</span>
            <span class="pp-air-cell-val font-mono text-warning">${roomPmPeak ? roomPmPeak.val : '—'} <span class="text-xs font-normal text-base-content/60">µg/m³</span></span>
            <span class="pp-air-cell-sub">${roomPmPeak ? `发生于 ${formatTime(roomPmPeak.ts)}` : '无峰值'}</span>
          </div>
          <div class="pp-air-cell">
            <span class="pp-air-cell-label">近30分钟变化</span>
            <span class="pp-air-cell-val text-sm font-semibold ${roomPmTrend.cls}">${roomPmTrend.text}</span>
            <span class="pp-air-cell-sub">${roomPmTrend.diffStr || '30分钟窗口'}</span>
          </div>
        </div>
      </div>

      <!-- 2. 移动测点 B TVOC -->
      <div class="pp-air-summary-col">
        <div class="pp-air-summary-col-head">
          <span class="pp-air-summary-col-title">${ppIcon("wind", "w-3.5 h-3.5 text-secondary")} 2. 移动测点 B TVOC</span>
          <span class="badge badge-xs ${telem.mobile.fresh ? 'badge-secondary badge-outline' : 'badge-ghost'}">${telem.mobile.fresh ? '实时' : '未更新'}</span>
        </div>
        <div class="pp-air-summary-cells">
          <div class="pp-air-cell">
            <span class="pp-air-cell-label">最新采样</span>
            <span class="pp-air-cell-val font-mono ${telem.mobile.fresh ? 'text-secondary' : 'text-base-content/60'}">${telem.mobile.tvoc != null ? telem.mobile.tvoc : '—'} <span class="text-xs font-normal text-base-content/60">ppb</span></span>
            <span class="pp-air-cell-sub">${telem.mobile.ageStr} · ${telem.mobile.fresh ? '实时' : '历史'}</span>
          </div>
          <div class="pp-air-cell">
            <span class="pp-air-cell-label">区间峰值</span>
            <span class="pp-air-cell-val font-mono text-secondary">${mobTvocPeak ? mobTvocPeak.val : '—'} <span class="text-xs font-normal text-base-content/60">ppb</span></span>
            <span class="pp-air-cell-sub">${mobTvocPeak ? `发生于 ${formatTime(mobTvocPeak.ts)}` : '选区无数据'}</span>
          </div>
          <div class="pp-air-cell">
            <span class="pp-air-cell-label">近30分钟变化</span>
            <span class="pp-air-cell-val text-sm font-semibold ${mobTvocTrend.cls}">${mobTvocTrend.text}</span>
            <span class="pp-air-cell-sub">${mobTvocTrend.diffStr || '30分钟窗口'}</span>
          </div>
        </div>
      </div>

      <!-- 3. 打印仓内温度 -->
      <div class="pp-air-summary-col">
        <div class="pp-air-summary-col-head">
          <span class="pp-air-summary-col-title">${ppIcon("spool", "w-3.5 h-3.5 text-accent")} 3. 打印仓内温度</span>
          <span class="badge badge-xs ${telem.chamber.exhaustOn ? 'badge-info' : 'badge-ghost'}">${telem.chamber.exhaustOn ? '排风开启' : '排风待机'}</span>
        </div>
        <div class="pp-air-summary-cells">
          <div class="pp-air-cell">
            <span class="pp-air-cell-label">最新采样</span>
            <span class="pp-air-cell-val font-mono text-accent">${telem.chamber.t_c != null ? telem.chamber.t_c : '—'} <span class="text-xs font-normal text-base-content/60">℃</span></span>
            <span class="pp-air-cell-sub">${telem.chamber.ageStr} · ${telem.room.fresh ? '实时' : '历史'}</span>
          </div>
          <div class="pp-air-cell">
            <span class="pp-air-cell-label">区间峰值</span>
            <span class="pp-air-cell-val font-mono text-accent">${chamberTempPeak ? chamberTempPeak.val : '—'} <span class="text-xs font-normal text-base-content/60">℃</span></span>
            <span class="pp-air-cell-sub">${chamberTempPeak ? `发生于 ${formatTime(chamberTempPeak.ts)}` : '无峰值'}</span>
          </div>
          <div class="pp-air-cell">
            <span class="pp-air-cell-label">近30分钟变化</span>
            <span class="pp-air-cell-val text-sm font-semibold ${chamberTempTrend.cls}">${chamberTempTrend.text}</span>
            <span class="pp-air-cell-sub">${chamberTempTrend.diffStr || '30分钟窗口'}</span>
          </div>
        </div>
      </div>
    </div>
  `;

  // 共享背景染色控制 HTML
  const bgControlsHtml = `
    <div class="flex items-center gap-2 flex-wrap">
      <label class="cursor-pointer inline-flex items-center gap-1.5 px-2 py-0.5 bg-base-200/50 rounded-lg text-xs hover:bg-base-200 transition select-none">
        <input type="checkbox" class="checkbox checkbox-xs text-emerald-500 rounded chk-bg-print" ${showBgPrint ? 'checked' : ''} />
        <span class="inline-block w-2.5 h-2.5 rounded bg-emerald-500/25 border border-emerald-500/50"></span>
        <span class="text-base-content/75 text-[11px]">A1 打印时段 (浅绿)</span>
      </label>
      <label class="cursor-pointer inline-flex items-center gap-1.5 px-2 py-0.5 bg-base-200/50 rounded-lg text-xs hover:bg-base-200 transition select-none">
        <input type="checkbox" class="checkbox checkbox-xs text-blue-500 rounded chk-bg-pres" ${showBgPresence ? 'checked' : ''} />
        <span class="inline-block w-2.5 h-2.5 rounded bg-blue-500/25 border border-blue-500/50"></span>
        <span class="text-base-content/75 text-[11px]">人员在场 (浅蓝)</span>
      </label>
    </div>
  `;

  // 模块一：颗粒物观察 (PM 模块)
  const modulePmHtml = `
    <div class="pp-air-module-card">
      <div class="pp-air-module-head">
        <div>
          <div class="pp-air-module-title">
            ${ppIcon("flask", "w-4 h-4 text-primary")}
            <span>颗粒物监测 · 打印房间 (PMS5003)</span>
          </div>
          <div class="text-[11px] text-base-content/50 mt-0.5">
            观察打印活动、人员存在与颗粒物读数的时间对应关系
          </div>
        </div>
        <div class="flex items-center gap-3 flex-wrap">
          <div class="flex items-center gap-2.5 text-xs">
            <label class="cursor-pointer flex items-center gap-1">
              <input type="checkbox" id="chk-pm1" class="checkbox checkbox-xs rounded" ${showPm1 ? 'checked' : ''} />
              <span class="text-base-content/70 text-[11px]">PM1.0</span>
            </label>
            <label class="cursor-pointer flex items-center gap-1">
              <input type="checkbox" id="chk-pm10" class="checkbox checkbox-xs rounded" ${showPm10 ? 'checked' : ''} />
              <span class="text-base-content/70 text-[11px]">PM10</span>
            </label>
          </div>
          ${bgControlsHtml}
          <span class="text-[11px] text-amber-500 font-mono">--- 35 µg/m³ 自定提醒</span>
        </div>
      </div>
      <div id="air-chart-pm" style="height: 320px; width: 100%;"></div>
      <details class="mt-2 text-xs text-base-content/60">
        <summary class="cursor-pointer select-none text-[11px] opacity-75 hover:opacity-100 flex items-center gap-1">
          <span>统计详情（均值 / 样本数 / 阈值）▼</span>
        </summary>
        <div class="p-2.5 mt-1 bg-base-200/40 rounded-xl flex items-center gap-6 flex-wrap font-mono text-[11px]">
          <span>区间均值: <b>${roomPmAvg != null ? `${roomPmAvg} µg/m³` : '—'}</b></span>
          <span>有效样本: <b>${roomPmPoints.length} 笔</b></span>
          <span>自定提醒线: <b>35 µg/m³</b></span>
        </div>
      </details>
    </div>
  `;

  // 模块二：气相物观察 (TVOC 模块)
  const moduleTvocHtml = `
    <div class="pp-air-module-card">
      <div class="pp-air-module-head">
        <div>
          <div class="pp-air-module-title">
            ${ppIcon("wind", "w-4 h-4 text-purple-500")}
            <span>气相物监测 · 仓内 vs 移动测点</span>
          </div>
          <div class="text-[11px] text-base-content/50 mt-0.5">
            背景标示打印区事件（不代表测点 B 所在位置）；测点 B (${esc(telem.mobile.location)}) 在离线期间断线保持真实间隙
          </div>
        </div>
        <div class="flex items-center gap-3 flex-wrap">
          ${bgControlsHtml}
          <span class="text-[11px] text-rose-500 font-mono">--- 220 ppb 自定提醒</span>
        </div>
      </div>
      <div id="air-chart-tvoc" style="height: 300px; width: 100%;"></div>
      <details class="mt-2 text-xs text-base-content/60">
        <summary class="cursor-pointer select-none text-[11px] opacity-75 hover:opacity-100 flex items-center gap-1">
          <span>统计详情（仓内 / 移动测点对比明细）▼</span>
        </summary>
        <div class="p-2.5 mt-1 bg-base-200/40 rounded-xl flex items-center gap-6 flex-wrap font-mono text-[11px]">
          <span>仓内 TVOC 均值: <b>${chamberTvocPoints.length ? Math.round(chamberTvocPoints.reduce((s, p) => s + p[1], 0) / chamberTvocPoints.length) : '—'} ppb</b> (${chamberTvocPoints.length} 笔)</span>
          <span>移动测点有效样本: <b>${mobTvocPoints.length} 笔</b> (${telem.mobile.fresh ? '实时' : telem.mobile.status})</span>
          <span>自定提醒线: <b>220 ppb</b></span>
        </div>
      </details>
    </div>
  `;

  // 模块三：温湿度与机箱工况 (环境模块)
  const moduleEnvHtml = `
    <div class="pp-air-module-card">
      <div class="pp-air-module-head">
        <div>
          <div class="pp-air-module-title">
            ${ppIcon("flame", "w-4 h-4 text-amber-500")}
            <span>温湿度与环境平衡 · 仓内 vs 房间</span>
          </div>
          <div class="text-[11px] text-base-content/50 mt-0.5">
            左轴温度 (实线 · ℃) · 右轴相对湿度 (虚线 · %) · 观察加热与通风状态下的温湿平衡
          </div>
        </div>
      </div>
      <div id="air-chart-env" style="height: 320px; width: 100%;"></div>
      <details class="mt-2 text-xs text-base-content/60">
        <summary class="cursor-pointer select-none text-[11px] opacity-75 hover:opacity-100 flex items-center gap-1">
          <span>统计详情（温湿度均值明细）▼</span>
        </summary>
        <div class="p-2.5 mt-1 bg-base-200/40 rounded-xl flex items-center gap-6 flex-wrap font-mono text-[11px]">
          <span>仓内均温: <b>${chamberTempAvg != null ? `${chamberTempAvg} ℃` : '—'}</b></span>
          <span>仓内样本: <b>${chamberTempPoints.length} 笔</b></span>
        </div>
      </details>
    </div>
  `;

  // 模块四：折叠原始明细
  const rawTableHtml = `
    <details class="card bg-base-100 border border-base-300/80 p-4 shadow-sm rounded-2xl mb-8">
      <summary class="flex items-center justify-between cursor-pointer select-none font-semibold text-sm">
        <div class="flex items-center gap-2">
          <span>📋</span>
          <span>传感器采样流水明细</span>
          <span class="text-xs text-base-content/50 font-mono font-normal">（默认折叠 · 显示最近 20 笔记录 · 共 ${rows.length} 条）</span>
        </div>
        <span class="text-xs text-primary font-normal">展开/收起 ▼</span>
      </summary>
      <div class="overflow-x-auto mt-3 pt-3 border-t border-base-200">
        <table class="table table-zebra table-sm w-full font-mono text-xs">
          <thead>
            <tr class="text-base-content/70">
              <th>时间</th>
              <th>测点区域</th>
              <th>地点</th>
              <th>仓内温湿</th>
              <th>房间温湿</th>
              <th>PM2.5</th>
              <th>PM1/10</th>
              <th>TVOC</th>
              <th>eCO₂等效</th>
              <th>机台状态</th>
            </tr>
          </thead>
          <tbody>
            ${rows.slice(0, 20).map((r) => {
              const x = r.data || {};
              const pr = x.printing == null ? "—" : (x.printing ? '<span class="badge badge-success badge-xs">打印中</span>' : '<span class="badge badge-ghost badge-xs">空闲</span>');
              const zLabel = r.zone === "mobile" ? "移动测点B" : (r.zone === "room" ? "打印房间A" : (r.zone || "—"));
              return `<tr>
                <td>${new Date(r.ts * 1000).toLocaleTimeString()}</td>
                <td><span class="badge ${r.zone === "mobile" ? "badge-primary badge-outline" : "badge-ghost"} badge-xs">${esc(zLabel)}</span></td>
                <td>${esc(x.location || "—")}</td>
                <td>${x.chamber_t_c != null ? `${x.chamber_t_c}℃ / ${x.chamber_rh}%` : "—"}</td>
                <td>${x.t_c != null ? `${x.t_c}℃ / ${x.rh}%` : "—"}</td>
                <td class="font-bold ${x.pm25 && x.pm25 > 35 ? "text-warning" : "text-success"}">${x.pm25 ?? "—"}</td>
                <td>${x.pm1 != null ? `${x.pm1}/${x.pm10}` : "—"}</td>
                <td>${x.tvoc != null ? `${x.tvoc} ppb` : "—"}</td>
                <td>${x.eco2 != null ? `${x.eco2} ppm` : "—"}</td>
                <td>${pr}${x.filament ? ` <span class="text-base-content/50">${esc(x.filament)}</span>` : ""}</td>
              </tr>`;
            }).join("")}
          </tbody>
        </table>
      </div>
    </details>
  `;

  // 拼接全页 HTML
  $("#page").innerHTML = `
    <div class="pp-air-container">
      ${headerHtml}
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
        ${roomCardHtml}
        ${mobCardHtml}
        ${chamberCardHtml}
      </div>
      ${summaryStripHtml}
      ${modulePmHtml}
      ${moduleTvocHtml}
      ${moduleEnvHtml}
      ${rawTableHtml}
    </div>
  `;

  // 绑定时间跨度按钮 (1h / 6h / 24h)
  document.querySelectorAll("[data-air-range]").forEach((b) => {
    b.addEventListener("click", () => {
      localStorage.setItem("pp-air-range", b.dataset.airRange);
      viewAir();
    });
  });

  // 绑定颗粒子开关 (PM1 / PM10)
  const chk1 = document.getElementById("chk-pm1");
  const chk10 = document.getElementById("chk-pm10");
  if (chk1) {
    chk1.onchange = () => {
      localStorage.setItem("pp-air-pm1", chk1.checked ? "true" : "false");
      viewAir();
    };
  }
  if (chk10) {
    chk10.onchange = () => {
      localStorage.setItem("pp-air-pm10", chk10.checked ? "true" : "false");
      viewAir();
    };
  }

  // 绑定背景图例开关
  document.querySelectorAll(".chk-bg-print").forEach((chk) => {
    chk.onchange = () => {
      localStorage.setItem("pp-air-bg-print", chk.checked ? "true" : "false");
      viewAir();
    };
  });
  document.querySelectorAll(".chk-bg-pres").forEach((chk) => {
    chk.onchange = () => {
      localStorage.setItem("pp-air-bg-pres", chk.checked ? "true" : "false");
      viewAir();
    };
  });

  // 初始化三大模块图表并统一联动
  if (window.echarts) {
    const dark = document.documentElement.getAttribute("data-theme") === "dark";
    const elPm = document.getElementById("air-chart-pm");
    const elTvoc = document.getElementById("air-chart-tvoc");
    const elEnv = document.getElementById("air-chart-env");

    let pmChart = null;
    let tvocChart = null;
    let envChart = null;

    if (elPm) {
      pmChart = echarts.init(elPm);
      pmChart.setOption(buildPmChartOption(range, asc, dark, { showPm1, showPm10, showBgPrint, showBgPresence }));
      window.__airCharts.push(pmChart);
    }
    if (elTvoc) {
      tvocChart = echarts.init(elTvoc);
      tvocChart.setOption(buildTvocChartOption(range, asc, dark, { mobLocation: telem.mobile.location, showBgPrint, showBgPresence }));
      window.__airCharts.push(tvocChart);
    }
    if (elEnv) {
      envChart = echarts.init(elEnv);
      envChart.setOption(buildEnvChartOption(range, asc, dark));
      window.__airCharts.push(envChart);
    }

    // 统一连结三张图的时间鼠标悬停十字线
    if (window.__airCharts.length > 1) {
      try {
        echarts.connect(window.__airCharts);
      } catch (e) {}
    }

    if (!window.__airResizeHooked) {
      window.__airResizeHooked = true;
      window.addEventListener("resize", () => {
        if (window.__airCharts && Array.isArray(window.__airCharts)) {
          window.__airCharts.forEach((c) => { try { c.resize(); } catch {} });
        }
      });
    }
  }
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
    <div class="flex flex-wrap items-center justify-between gap-3 border-b border-base-300/60 pb-3 mb-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight mb-0.5 flex items-center gap-2">
          ${ppIcon("cog", "w-6 h-6 text-primary")}
          <span>系统设置与集成中枢</span>
        </h1>
        <p class="text-xs text-base-content/60">集中管理拓竹云同步、AI 视觉识图、萤石监控、易微联智能插座及企业微信通知。</p>
      </div>
      <button type="button" class="btn btn-primary btn-sm gap-1 shadow-sm" id="sa">
        <span>💾</span> 保存全部设置
      </button>
    </div>

    <!-- 分类快速筛选 Tab -->
    <div class="flex items-center gap-1.5 overflow-x-auto pb-2 mb-4 pp-tab-group" id="settings-tabs">
      <button type="button" class="pp-tab-btn active" data-cat="all">全部设置</button>
      <button type="button" class="pp-tab-btn" data-cat="site">站点与账号</button>
      <button type="button" class="pp-tab-btn" data-cat="bambu">拓竹云</button>
      <button type="button" class="pp-tab-btn" data-cat="ewelink">智能插座</button>
      <button type="button" class="pp-tab-btn" data-cat="ezviz">萤石监控</button>
      <button type="button" class="pp-tab-btn" data-cat="ai">AI 识图</button>
      <button type="button" class="pp-tab-btn" data-cat="token">硬件令牌</button>
      <button type="button" class="pp-tab-btn" data-cat="wecom">企业微信</button>
    </div>

    <div class="pp-settings-grid" id="settings-cards">
    ${card(`
      <h2 class="card-title text-base font-bold flex items-center gap-1.5 mb-2">
        <span>🌐</span> 站点与管理员账号
      </h2>
      <div class="row cols-2">
        ${field("站点名称", inputEl("st", `value="${esc(s.site.title)}"`))}
        ${field("用户名", inputEl("su", `value="${esc(me.username)}"`))}
        ${field("原密码", inputEl("so", `type="password" placeholder="改密码时必填"`))}
        ${field("新密码", inputEl("sn", `type="password" placeholder="留空不改密码"`))}
      </div>
      <div class="card-actions mt-3">
        <button class="btn btn-primary btn-sm" id="ssite">保存站点名称</button>
        <button class="btn btn-ghost btn-sm" id="spw">修改用户名密码</button>
      </div>
    `, "setcat-site")}
    ${card(`
      <h2 class="card-title text-base font-bold flex items-center gap-1.5 mb-1">
        <span>🤖</span> AI 视觉识别配置 (Vision API)
      </h2>
      <p class="muted text-xs mb-2">耗材包装贴纸、TDS 规格表上传后由视觉大模型自动提取工况参数。支持 OpenAI 兼容格式（ChatGPT、通义千问、SiliconFlow、DeepSeek等）或 Gemini。</p>
      <div class="row cols-2">
        ${field("接口地址 (Base URL)", inputEl("ai_endpoint", `value="${esc(s.ai?.endpoint || "")}" placeholder="默认: https://api.openai.com/v1"`))}
        ${field("视觉模型名称 (Model)", inputEl("ai_model", `value="${esc(s.ai?.model || "")}" placeholder="默认: gpt-4o-mini 或 qwen-vl-plus / gemini-1.5-flash"`))}
      </div>
      <div class="row cols-2">
        ${field("API Key", inputEl("ai_key", `type="password" value="${esc(s.ai?.api_key || "")}" placeholder="输入视觉模型 API Key (如 sk-...)"`))}
        ${field("AI 令牌（外部系统接入）", inputEl("ait", `value="${esc(s.ai?.token || "")}" placeholder="留空表示保留原值"`))}
      </div>
      <div class="card-actions mt-3">
        <button class="btn btn-primary btn-sm" id="saveai">保存 AI 设置</button>
      </div>
    `, "setcat-ai")}
    ${card(`
      <h2 class="card-title text-base font-bold flex items-center gap-1.5 mb-1">
        <span>🔑</span> ESP32 硬件设备令牌
      </h2>
      <p class="muted text-xs mb-2">空气探头与桌面端访问本站用的密钥，已脱敏显示——留空保存表示保留原值。</p>
      <div class="row cols-2">
        ${field("空气令牌（ESP32 探头）", inputEl("at", `value="${esc(s.air.token)}" placeholder="留空表示保留原值"`))}
      </div>
    `, "setcat-token")}
    ${card(`
      <h2 class="card-title text-base font-bold flex items-center gap-1.5 mb-1">
        <span>🖨️</span> 拓竹云账号 (Bambu Cloud)
      </h2>
      <p class="muted text-xs mb-2">云端耗材目录与打印机连接的数据源。登录三步：<b>① 保存账号 → ② 发送验证码 → ③ 验证码登录</b>，成功后记住 token，之后免验证。</p>
      <div class="row cols-2">
        ${field("地区", inputEl("br", `value="${esc(s.bambu.region)}"`))}
        ${field("打印机 SN", inputEl("bsn", `value="${esc(s.bambu.printer_sn)}"`))}
        ${field("账号（手机或邮箱）", inputEl("ba", `value="${esc(s.bambu.account)}"`))}
        ${field("密码", inputEl("bp", `type="password" placeholder="不改请留空"`))}
        ${field("短信/邮箱验证码", inputEl("bc", `placeholder="6 位"`))}
        ${field("或粘贴 accessToken", inputEl("btok", `type="password" placeholder="可选，高级用法"`))}
      </div>
      <div class="card-actions flex-wrap mt-3">
        <button class="btn btn-ghost btn-sm" id="tb">① 保存账号</button>
        <button class="btn btn-ghost btn-sm" id="bcode">② 发送验证码</button>
        <button class="btn btn-primary btn-sm" id="bver">③ 验证码登录</button>
        <button class="btn btn-ghost btn-outline btn-sm" id="btoken">用 Token 登录（备用）</button>
      </div>
    `, "setcat-bambu")}
    ${card(`
      <h2 class="card-title text-base font-bold flex items-center gap-1.5 mb-1">
        <span>🔌</span> 易微联智能插座 (eWeLink)
      </h2>
      <p class="muted text-xs mb-2">补光灯、净化器等云插座的控制通道，手机 App 不受影响。填 App 同一套账号登录，设备列表里点选绑定，免手抄 ID。</p>
      <div class="row cols-2">
        ${field("地区（中国填 cn）", inputEl("er", `value="${esc(s.ewelink.region)}"`))}
        ${field("手机或邮箱", inputEl("ea", `value="${esc(s.ewelink.account)}" placeholder="138xxxx 或邮箱"`))}
        ${field("密码", inputEl("ep", `type="password" placeholder="已保存则留空"`))}
        ${field("打印后加强分钟", inputEl("emin", `type="number" value="${s.automations.print_boost_minutes}"`))}
      </div>
      ${field("或粘贴 Access Token（账号密码 407 时用）", inputEl("etok", `type="password" placeholder="从 web.ewelink.cc 复制 Bearer 后面那段"`))}
      <div class="collapse collapse-arrow bg-base-200 border border-base-300 my-2">
        <input type="checkbox" />
        <div class="collapse-title text-xs font-semibold">高级：自备 APPID（一般必须留空）</div>
        <div class="collapse-content">
          <div class="row cols-2">
            ${field("APPID", inputEl("eid", `value="" placeholder="留空"`))}
            ${field("APPSECRET", inputEl("es", `type="password" placeholder="留空"`))}
          </div>
          <p class="muted text-xs">开发者中心的官方 APPID 走账号密码会报 407。这里留空，用内置凭证。</p>
        </div>
      </div>
      <div class="card-actions flex-wrap mt-2">
        <button class="btn btn-primary btn-sm" id="te">登录并拉取设备</button>
        <button class="btn btn-ghost btn-sm" id="ewsave">只保存账号</button>
        <button class="btn btn-ghost btn-outline btn-sm" id="ewtok">用 Token 登录（备用）</button>
      </div>
      <div class="bind-summary" id="ebound">
        ${bindRow("补光灯", "el", s.ewelink.light)}
        ${bindRow("仓内长开", "eba", s.ewelink.box_always)}
        ${bindRow("仓内打印加强", "ebp", s.ewelink.box_print)}
        ${bindRow("车间有人", "ero", s.ewelink.room)}
      </div>
      <div id="elist"></div>
    `, "setcat-ewelink")}
    ${card(`
      <h2 class="card-title text-base font-bold flex items-center gap-1.5 mb-1">
        <span>📹</span> 萤石摄像头监控 (EZVIZ)
      </h2>
      <p class="text-sm muted mb-2">
        <a href="https://open.ys7.com/console/application.html" target="_blank" class="link link-hover">获取 AppKey / Secret</a>
        <span class="mx-1 opacity-40">·</span>
        <a href="https://open.ys7.com/console/device.html" target="_blank" class="link link-hover">查看设备序列号</a>
        <span class="mx-1 opacity-40">·</span>
        首次需在开放平台创建应用并配置后才能取到密钥
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
      <div class="card-actions"><button class="btn btn-primary" id="tz">保存并测试画面</button></div>
    `, "setcat-ezviz")}
    ${card(`
      <h2 class="card-title">消息通知（企业微信）</h2>
      <p class="text-sm muted">首层完成与打印结束时自动抓监控图推送到微信，免费。</p>
      <div class="mt-2">
        <div class="font-bold border-b pb-1 mb-2">首次接入步骤</div>
        <ol class="text-xs muted mb-3" style="line-height:1.8;padding-left:1.2em;list-style:decimal">
          <li><a href="https://work.weixin.qq.com" target="_blank" class="link">注册/登录企业微信后台</a> → 应用管理 → 创建应用</li>
          <li>在应用「接收消息」处填写 URL：<code id="wecom-webhook-url">${hookUrl}</code>，记下 Token 和 EncodingAESKey</li>
          <li>将 企业ID / Secret / AgentID / AESKey 填入下方，点「保存通知设置」</li>
          <li>回到企业微信页面点保存；最后把「企业可信IP」设为 <code id="wecom-server-ip">${serverIp}</code></li>
        </ol>
        <div class="row cols-3 mb-2">
          ${field("企业ID (CorpID)", inputEl("wcCorp", `value="${esc(s.automations.wecom_corpid || "")}" placeholder="ww..."`))}
          ${field("应用Secret", inputEl("wcSec", `type="password" placeholder="留空不改"`))}
          ${field("应用 AgentID", inputEl("wcAgent", `value="${esc(s.automations.wecom_agentid || "")}" placeholder="1000002"`))}
        </div>
        <div class="row cols-2 mb-3">
          ${field("EncodingAESKey", inputEl("wcAES", `type="password" placeholder="用于过检URL验证"`))}
          ${field("接收人（留空发全体）", inputEl("wcTo", `value="${esc(s.automations.wecom_touser || "")}" placeholder="@all 或 账号ID"`))}
        </div>
      </div>
      <div class="card-actions mt-3">
        <button class="btn btn-primary" id="savewh">保存通知设置</button>
        <button class="btn btn-outline" id="testwh">发送测试推送</button>
      </div>
    `, "card-wide setcat-wecom")}
    </div>`;
  const collect = () => ({
    site: { title: $("#st").value },
    bambu: { region: $("#br").value, account: $("#ba").value, password: $("#bp").value, printer_sn: $("#bsn").value },
    ewelink: { region: $("#er").value, account: $("#ea").value, password: $("#ep").value, app_id: $("#eid")?.value || "", app_secret: $("#es")?.value || "",
      light: $("#el").value, box_always: $("#eba").value, box_print: $("#ebp").value, room: $("#ero").value },
    ezviz: { app_key: $("#zk").value, app_secret: $("#zs").value, device_serial: $("#zd").value, channel: $("#zc").value, verify_code: $("#zvc")?.value || "", rotation: $("#zr")?.value || "", crop: `${$("#zc_t")?.value||0},${$("#zc_b")?.value||0},${$("#zc_l")?.value||0},${$("#zc_r")?.value||0}` },
    air: { token: $("#at").value },
    ai: {
      token: $("#ait")?.value || "",
      endpoint: $("#ai_endpoint")?.value?.trim() || "",
      api_key: $("#ai_key")?.value?.trim() || "",
      model: $("#ai_model")?.value?.trim() || "",
    },
    automations: { box_always_on: true, print_boost_minutes: Number($("#emin").value), room_on_presence: true, wecom_corpid: $("#wcCorp")?.value || "", wecom_secret: $("#wcSec")?.value || "", wecom_agentid: $("#wcAgent")?.value || "", wecom_aeskey: $("#wcAES")?.value || "", wecom_touser: $("#wcTo")?.value || "" },
  });
  if ($("#saveai")) $("#saveai").onclick = (e) => busy(e.currentTarget, async () => {
    await api("/api/settings", { method: "PUT", body: collect() });
    toast("AI 设置已保存", "success");
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

  $("#settings-tabs")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-cat]");
    if (!btn) return;
    document.querySelectorAll("#settings-tabs .pp-tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    const cat = btn.dataset.cat;
    document.querySelectorAll("#settings-cards > .card, .pp-settings-grid > .card, .masonry-grid > section").forEach(cardEl => {
      if (cat === "all" || cardEl.classList.contains(`setcat-${cat}`)) {
        cardEl.style.display = "";
      } else {
        cardEl.style.display = "none";
      }
    });
  });
}

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
        const bv = (s.bambu_vendor || "").toLowerCase();
        if (!sc.includes(term) && !fn.includes(term) && !bv.includes(term)) return false;
      }
      return true;
    });

    const totalCount = spools.length;
    const openedCount = spools.filter(s => s.status === 'opened').length;
    const unopenedCount = spools.filter(s => s.status === 'unopened').length;
    const depletedCount = spools.filter(s => s.status === 'depleted').length;

    $("#page").innerHTML = `
      <div class="flex flex-wrap justify-between items-center gap-3 border-b border-base-300/60 pb-3 mb-5">
        <div>
          <h1 class="text-2xl font-bold tracking-tight mb-0.5 flex items-center gap-2">
            ${ppIcon("spool", "w-6 h-6 text-primary")}
            <span>物理料盘台账</span>
          </h1>
          <p class="text-xs text-base-content/60">共登记 ${totalCount} 盘物理线盘资产 · 拓竹云端真实档案与短编号 (PP-xxx) 贴标对齐，开封状态与剩余净重双向同步。</p>
        </div>
        <div class="flex items-center gap-2">
          <a href="#/stock" class="btn btn-sm btn-outline gap-1 border-base-content/20">
            ${ppIcon("matrix")} <span>架子盘点</span>
          </a>
          <button class="btn btn-sm btn-primary gap-1 shadow-sm" id="btn-cloud-sync">
            <span>⚡</span> 从拓竹云同步
          </button>
        </div>
      </div>

      <!-- 4 大统计汇总卡 -->
      <div class="pp-kpi-grid">
        ${statCard({
          icon: ppIcon("spool", "w-3.5 h-3.5"),
          title: "料盘总数",
          status: "物理台账全量",
          statusCls: "text-base-content/80",
          val: totalCount,
          unit: "盘",
          aux: [["资产范围", "已登记实体线盘"], ["云端状态", "拓竹云双向对齐"]],
          meta: "含已开封使用与密封备库"
        })}
        ${statCard({
          icon: ppIcon("flame", "w-3.5 h-3.5"),
          title: "已开封使用中",
          status: "随时可用",
          statusCls: "text-warning",
          val: openedCount,
          unit: "盘",
          aux: [["存放位置", "干燥箱/料架在线"], ["占比", totalCount ? `${Math.round(openedCount / totalCount * 100)}%` : "0%"]],
          meta: "建议定期检查密封与湿度"
        })}
        ${statCard({
          icon: ppIcon("flask", "w-3.5 h-3.5"),
          title: "全新未拆封",
          status: "密封备库",
          statusCls: "text-success",
          val: unopenedCount,
          unit: "盘",
          aux: [["包装状态", "真空铝箔包装完整"], ["占比", totalCount ? `${Math.round(unopenedCount / totalCount * 100)}%` : "0%"]],
          meta: "未拆封无需占用干燥箱"
        })}
        ${statCard({
          icon: ppIcon("exit", "w-3.5 h-3.5"),
          title: "空盘 / 已用尽",
          status: "待收纳归档",
          statusCls: "text-base-content/50",
          val: depletedCount,
          unit: "盘",
          aux: [["盘体处置", "待清理或复用盘体"], ["占比", totalCount ? `${Math.round(depletedCount / totalCount * 100)}%` : "0%"]],
          meta: "已归档物理空盘"
        })}
      </div>

      <!-- 搜索与状态过滤器 -->
      <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
        <input type="text" id="spool-search" placeholder="搜索短编号 (如 PP-012)、耗材名称或品牌..." class="input input-bordered input-sm flex-1 min-w-[220px] rounded-xl" value="${esc(currentSearch)}">
        <div class="tabs tabs-boxed bg-base-200/80 p-1 rounded-xl">
          <a class="tab tab-sm ${currentFilter === 'all' ? 'tab-active font-bold' : ''}" data-filter="all">全部 (${totalCount})</a>
          <a class="tab tab-sm ${currentFilter === 'opened' ? 'tab-active font-bold' : ''}" data-filter="opened">已开封 (${openedCount})</a>
          <a class="tab tab-sm ${currentFilter === 'unopened' ? 'tab-active font-bold' : ''}" data-filter="unopened">未开封 (${unopenedCount})</a>
          <a class="tab tab-sm ${currentFilter === 'depleted' ? 'tab-active font-bold' : ''}" data-filter="depleted">已用完 (${depletedCount})</a>
        </div>
      </div>

      <!-- 料盘数据表格 -->
      <div class="overflow-x-auto rounded-2xl border border-base-300/80 bg-base-100 shadow-sm">
        <table class="table table-zebra table-sm w-full">
          <thead>
            <tr class="bg-base-200/60 text-base-content/70 text-xs">
              <th class="w-24 py-3.5 pl-4">短编号</th>
              <th>品牌与耗材型号</th>
              <th class="w-32">当前状态</th>
              <th class="w-28">净重 / 余量</th>
              <th class="hide-on-mobile">云端最近同步</th>
              <th class="w-28 text-right pr-4">操作</th>
            </tr>
          </thead>
          <tbody id="spools-body">
            ${filtered.map(s => {
              const fname = dedupeName(s.bambu_filament_name) || s.short_code;
              const hex = (s.color_hex || "").toLowerCase();
              const swatch = /^[0-9a-f]{6}$/.test(hex) ? `<span class="inline-block w-3.5 h-3.5 rounded-full border border-base-300 mr-2 align-middle shadow-sm" style="background:#${hex}"></span>` : "";
              return `
              <tr class="hover:bg-base-200/40 transition">
                <td class="pl-4 py-3"><span class="badge badge-primary badge-outline font-mono font-bold badge-sm">${esc(s.short_code || "—")}</span></td>
                <td class="py-3">
                  <div class="font-bold flex items-center text-sm">${swatch}${s.bambu_vendor ? `<span class="opacity-70 mr-1 font-normal">${esc(s.bambu_vendor)}</span>` : ""}${esc(fname)}</div>
                  <div class="text-[11px] text-base-content/50 hide-on-mobile font-mono mt-0.5">Cloud ID: ${s.bambu_cloud_id || "未绑定"} ${s.bambu_filament_id ? `· ${esc(s.bambu_filament_id)}` : ""}</div>
                </td>
                <td class="py-3">
                  <select class="select select-bordered select-xs font-medium w-full max-w-[110px]" data-sp-id="${esc(s.id)}" data-sp-act="status">
                    <option value="opened" ${s.status === "opened" ? "selected" : ""}>● 已开封</option>
                    <option value="unopened" ${s.status === "unopened" ? "selected" : ""}>○ 未开封</option>
                    <option value="depleted" ${s.status === "depleted" ? "selected" : ""}>已用完</option>
                  </select>
                </td>
                <td class="py-3">
                  <div class="flex items-center gap-1">
                    <span class="font-mono font-semibold tabular-nums text-sm text-base-content/90 cursor-pointer hover:underline" title="点击修改重量" data-sp-id="${esc(s.id)}" data-sp-act="weight" data-sp-code="${esc(s.short_code || '')}" data-sp-name="${esc(fname)}" data-sp-weight="${s.net_weight_g != null ? Math.round(s.net_weight_g) : 1000}">${s.net_weight_g != null ? Math.round(s.net_weight_g) + " g" : "—"}</span>
                  </div>
                </td>
                <td class="py-3 text-xs text-base-content/60 hide-on-mobile font-mono">${s.last_synced_at ? esc(fmtLocalMinute(s.last_synced_at)) : "从未同步"}</td>
                <td class="py-3 text-right pr-4">
                  <div class="inline-flex items-center gap-1">
                    <button type="button" class="btn btn-xs btn-ghost gap-1 px-2" title="修改重量" data-sp-id="${esc(s.id)}" data-sp-act="weight" data-sp-code="${esc(s.short_code || '')}" data-sp-name="${esc(fname)}" data-sp-weight="${s.net_weight_g != null ? Math.round(s.net_weight_g) : 1000}">
                      ${ppIcon("edit", "w-3 h-3")}<span>改重</span>
                    </button>
                    <button type="button" class="btn btn-xs btn-ghost text-error gap-1 px-2 hover:bg-error/10" title="报废删除" data-sp-id="${esc(s.id)}" data-sp-act="delete" data-sp-code="${esc(s.short_code || '')}" data-sp-name="${esc(fname)}">
                      ${ppIcon("trash", "w-3 h-3")}<span>报废</span>
                    </button>
                  </div>
                </td>
              </tr>
            `}).join("")}
            ${filtered.length === 0 ? `<tr><td colspan="6" class="text-center py-12 text-base-content/50">没有匹配的料盘记录。${currentSearch ? `已按「${esc(currentSearch)}」过滤，可清空搜索词。` : `点击右上角「从拓竹云同步」拉取数据。`}</td></tr>` : ""}
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

    $("#spools-body")?.addEventListener("change", async (e) => {
      const sel = e.target.closest("select[data-sp-act='status']");
      if (!sel) return;
      const id = sel.dataset.spId;
      const newStatus = sel.value;
      sel.disabled = true;
      try {
        await api("/api/spools/" + id + "/status", { method: "PUT", body: { status: newStatus } });
        toast(newStatus === "depleted" ? "料盘已标记为已用完（移出在架台账）" : "料盘状态已更新", "success");
        const sp = (spools || []).find(x => x.id === id);
        if (sp) sp.status = newStatus;
        render();
      } catch (ex) {
        toast(ex.message, "error");
        render();
      }
    });

    $("#spools-body")?.addEventListener("click", (e) => {
      const wBtn = e.target.closest("[data-sp-act='weight']");
      if (wBtn) {
        const id = wBtn.dataset.spId;
        const code = wBtn.dataset.spCode;
        const name = wBtn.dataset.spName;
        const curW = Number(wBtn.dataset.spWeight) || 0;
        window.openEditWeightModal(id, curW, 1000, `修改重量：${code}`, `${name} · 实际称重或估算净重`, () => {
          viewSpools();
        });
        return;
      }
      const dBtn = e.target.closest("[data-sp-act='delete']");
      if (dBtn) {
        const id = dBtn.dataset.spId;
        const code = dBtn.dataset.spCode;
        const name = dBtn.dataset.spName;
        window.confirmDanger(`确定要报废料盘「${code} ${name}」吗？此操作将从本地与云端彻底删除此盘资产记录。`, async () => {
          try {
            await api("/api/spools/" + id, { method: "DELETE" });
            toast(`料盘 ${code} 已报废删除`, "success");
            viewSpools();
          } catch (ex) {
            toast(ex.message, "error");
          }
        });
        return;
      }
    });

    $("#btn-cloud-sync")?.addEventListener("click", (e) => {
      busy(e.currentTarget, async () => {
        try {
          await api("/api/spools/cloud/sync", { method: "POST" });
          toast("已从拓竹云同步最新耗材数据", "success");
          viewSpools();
        } catch (ex) {
          toast(ex.message, "error");
        }
      });
    });
  };

  render();
}

// ---- Global Weight Edit Modal Handler ----
window.openEditWeightModal = (spoolId, currentW, maxW = 1000, title = "", subtitle = "", onDone = null) => {
  const modal = document.getElementById("modal-spool-weight");
  if (!modal) return;
  const input = document.getElementById("modal-weight-input");
  const range = document.getElementById("modal-weight-range");
  const saveBtn = document.getElementById("modal-weight-save");
  const titleEl = document.getElementById("modal-weight-title");
  const subEl = document.getElementById("modal-weight-subtitle");

  if (titleEl) titleEl.innerText = title || "修改料盘净重";
  if (subEl) subEl.innerText = subtitle || "调整料盘剩余重量并同步记录";

  const safeW = Math.max(0, Math.round(Number(currentW) || 0));
  const safeMax = Math.max(1000, Math.round(Number(maxW) || 1000));
  range.max = safeMax;
  input.max = safeMax;
  input.value = safeW;
  range.value = Math.min(safeW, safeMax);

  input.oninput = () => {
    const val = Number(input.value) || 0;
    range.value = Math.min(val, safeMax);
  };
  range.oninput = () => {
    input.value = range.value;
  };
  window.setSpoolWeightPreset = (presetW) => {
    input.value = presetW;
    range.value = Math.min(presetW, safeMax);
  };

  saveBtn.onclick = async () => {
    const newW = Number(input.value);
    if (isNaN(newW) || newW < 0) {
      toast("请输入合法的重量数字", "warning");
      return;
    }
    saveBtn.disabled = true;
    try {
      await api("/api/spools/" + spoolId + "/weight", { method: "PUT", body: { net_weight_g: newW } });
      toast("料盘重量已更新", "success");
      modal.close();
      if (onDone) onDone();
    } catch (ex) {
      toast(ex.message, "error");
    } finally {
      saveBtn.disabled = false;
    }
  };

  modal.showModal();
};

// ---- Global Danger Modal Handler ----
window.confirmDanger = (msg, onConfirm) => {
  document.getElementById('modal-danger-msg').innerText = msg;
  const btn = document.getElementById('modal-danger-confirm');
  btn.onclick = () => {
    document.getElementById('modal-danger').close();
    onConfirm();
  };
  document.getElementById('modal-danger').showModal();
};

boot().catch((e) => { root.textContent = e.message; });
