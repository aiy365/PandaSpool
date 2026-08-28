import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { api } from "./api.js";

function useBoot() {
  const [boot, setBoot] = useState(null);
  useEffect(() => { api("/api/bootstrap").then(setBoot).catch(() => setBoot({ needs_setup: false })); }, []);
  return boot;
}

export default function App() {
  const boot = useBoot();
  const [me, setMe] = useState(null);
  const nav = useNavigate();
  useEffect(() => {
    if (!boot || boot.needs_setup) return;
    api("/api/me").then(setMe).catch(() => setMe(false));
  }, [boot]);
  if (!boot) return null;
  if (boot.needs_setup) return <Setup onDone={() => location.reload()} />;
  if (me === null) return null;
  if (me === false) return <Login onDone={(u) => setMe(u)} />;
  return (
    <div className="shell">
      <header className="top">
        <div className="brand">{me.title || "PrintPilot"}</div>
        <nav>
          <NavLink to="/" end>总览</NavLink>
          <NavLink to="/materials">耗材</NavLink>
          <NavLink to="/compare">横评</NavLink>
          <NavLink to="/machine">机台</NavLink>
          <NavLink to="/air">空气</NavLink>
          <NavLink to="/settings">设置</NavLink>
        </nav>
        <div className="grow" />
        <button className="btn ghost" onClick={async () => { await api("/api/logout", { method: "POST", body: {} }); setMe(false); nav("/"); }}>退出</button>
      </header>
      <main className="page">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/materials" element={<Materials />} />
          <Route path="/materials/:id" element={<Product />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/machine" element={<Machine />} />
          <Route path="/air" element={<Air />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}

function Setup({ onDone }) {
  const [f, setF] = useState({ username: "admin", password: "", title: "PrintPilot" });
  const [err, setErr] = useState("");
  return (
    <div className="auth"><form className="card" onSubmit={async (e) => {
      e.preventDefault();
      try { await api("/api/setup", { method: "POST", body: f }); onDone(); } catch (ex) { setErr(ex.message); }
    }}>
      <h1>初始化这台 PrintPilot</h1>
      <p className="muted">第一次打开。用户名密码只存在本机数据目录，可在设置页改。</p>
      <div className="row"><label>站点名称<input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></label></div>
      <div className="row cols-2">
        <label>管理员<input value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} /></label>
        <label>密码（≥6 位）<input type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></label>
      </div>
      {err && <p className="err">{err}</p>}
      <button className="btn" type="submit">开始使用</button>
    </form></div>
  );
}

function Login({ onDone }) {
  const [f, setF] = useState({ username: "", password: "" });
  const [err, setErr] = useState("");
  return (
    <div className="auth"><form className="card" onSubmit={async (e) => {
      e.preventDefault();
      try { await api("/api/login", { method: "POST", body: f }); onDone(await api("/api/me")); } catch (ex) { setErr(ex.message); }
    }}>
      <h1>登录</h1>
      <label>用户名<input value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} /></label>
      <label>密码<input type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></label>
      {err && <p className="err">{err}</p>}
      <button className="btn" type="submit">进入</button>
    </form></div>
  );
}

function Home() {
  const [d, setD] = useState(null);
  useEffect(() => { api("/api/summary").then(setD); }, []);
  if (!d) return null;
  const m = d.machine || {};
  return (
    <>
      <div className="row cols-4">
        <div className="card"><div className="muted">产品</div><div className="stat">{d.products}</div></div>
        <div className="card"><div className="muted">颜色</div><div className="stat">{d.colors}</div></div>
        <div className="card"><div className="muted">未开封 / 开封</div><div className="stat">{d.unopened} / {d.opened}</div></div>
        <div className="card"><div className="muted">架子当量</div><div className="stat">{d.spools}</div></div>
      </div>
      <div className="card">
        <h2>机台</h2>
        <p>状态 {m.gcode_state || m.stage || "—"}　进度 {m.progress ?? "—"}%　热床 {m.bed_temp ?? "—"}　喷嘴 {m.nozzle_temp ?? "—"}</p>
        <p className="muted">{m.error ? <span className="err">{m.error}</span> : m.connected ? <span className="ok">MQTT 已连接</span> : "未连接拓竹，去设置页填写"}</p>
      </div>
    </>
  );
}

function Materials() {
  const nav = useNavigate();
  const [list, setList] = useState([]);
  const [f, setF] = useState({ brand: "", product_line: "", material: "PLA", notes: "" });
  const load = () => api("/api/products").then(setList);
  useEffect(() => { load(); }, []);
  return (
    <>
      <div className="card">
        <h1>耗材</h1>
        <div className="row cols-3">
          <label>品牌<input value={f.brand} onChange={(e) => setF({ ...f, brand: e.target.value })} /></label>
          <label>系列<input value={f.product_line} onChange={(e) => setF({ ...f, product_line: e.target.value })} /></label>
          <label>材料<input value={f.material} onChange={(e) => setF({ ...f, material: e.target.value })} /></label>
        </div>
        <p><button className="btn" onClick={async () => { const p = await api("/api/products", { method: "POST", body: f }); nav("/materials/" + p.id); }}>新建产品</button></p>
      </div>
      {list.map((p) => (
        <div className="card" key={p.id} onClick={() => nav("/materials/" + p.id)} style={{ cursor: "pointer" }}>
          <strong>{p.brand} {p.product_line}</strong> <span className="pill">{p.material}</span>
          <div className="muted">{(p.colors || []).map((c) => `${c.name} ${c.unopened}+${c.opened ? "开" : "封"}`).join(" · ") || "还没有颜色"}</div>
        </div>
      ))}
    </>
  );
}

function Product() {
  const { id } = useParams();
  const nav = useNavigate();
  const [data, setData] = useState(null);
  const [color, setColor] = useState({ name: "", color_family: "", unopened: 0, opened: 0 });
  const [claim, setClaim] = useState({ source: "资料", key: "喷嘴温度", value: "", unit: "°C" });
  const load = () => api("/api/products/" + id).then(setData);
  useEffect(() => { load(); }, [id]);
  if (!data) return null;
  const p = data.product;
  return (
    <>
      <div className="card">
        <h1>{p.brand} {p.product_line}</h1>
        <div className="row cols-3">
          <label>品牌<input value={p.brand} onChange={(e) => setData({ ...data, product: { ...p, brand: e.target.value } })} /></label>
          <label>系列<input value={p.product_line} onChange={(e) => setData({ ...data, product: { ...p, product_line: e.target.value } })} /></label>
          <label>材料<input value={p.material} onChange={(e) => setData({ ...data, product: { ...p, material: e.target.value } })} /></label>
        </div>
        <label>备注<textarea value={p.notes} onChange={(e) => setData({ ...data, product: { ...p, notes: e.target.value } })} /></label>
        <p>
          <button className="btn" onClick={async () => { await api("/api/products/" + id, { method: "PUT", body: data.product }); load(); }}>保存产品</button>{" "}
          <button className="btn danger" onClick={async () => { await api("/api/products/" + id, { method: "DELETE" }); nav("/materials"); }}>删除</button>
        </p>
      </div>
      <div className="card">
        <h2>颜色库存（未开封卷 + 是否开封，没有余量%）</h2>
        <div className="row cols-4">
          <label>商家颜色名<input value={color.name} onChange={(e) => setColor({ ...color, name: e.target.value })} /></label>
          <label>色系<input value={color.color_family} onChange={(e) => setColor({ ...color, color_family: e.target.value })} /></label>
          <label>未开封<input type="number" value={color.unopened} onChange={(e) => setColor({ ...color, unopened: Number(e.target.value) })} /></label>
          <label>开封卷<select value={color.opened} onChange={(e) => setColor({ ...color, opened: Number(e.target.value) })}><option value={0}>无</option><option value={1}>有 1 卷</option></select></label>
        </div>
        <p><button className="btn" onClick={async () => { await api("/api/colors", { method: "POST", body: { ...color, product_id: id } }); setColor({ name: "", color_family: "", unopened: 0, opened: 0 }); load(); }}>加入颜色</button></p>
        <div className="table-wrap"><table className="table"><thead><tr><th>颜色</th><th>色系</th><th>未开封</th><th>开封</th><th></th></tr></thead>
          <tbody>{(p.colors || []).map((c) => (
            <tr key={c.id}><td>{c.name}</td><td>{c.color_family}</td><td>{c.unopened}</td><td>{c.opened ? "有" : "无"}</td>
              <td><button className="btn ghost" onClick={async () => { await api("/api/colors?id=" + c.id, { method: "DELETE" }); load(); }}>删</button></td></tr>
          ))}</tbody></table></div>
      </div>
      <div className="card">
        <h2>参数（来源分层，冲突并存）</h2>
        <div className="row cols-4">
          <label>来源<select value={claim.source} onChange={(e) => setClaim({ ...claim, source: e.target.value })}>
            <option>资料</option><option>Studio</option><option>实测</option>
          </select></label>
          <label>字段<input value={claim.key} onChange={(e) => setClaim({ ...claim, key: e.target.value })} /></label>
          <label>值<input value={claim.value} onChange={(e) => setClaim({ ...claim, value: e.target.value })} /></label>
          <label>单位<input value={claim.unit} onChange={(e) => setClaim({ ...claim, unit: e.target.value })} /></label>
        </div>
        <p><button className="btn" onClick={async () => { await api("/api/claims", { method: "POST", body: { ...claim, product_id: id } }); load(); }}>记一条</button></p>
        <div className="table-wrap"><table className="table"><thead><tr><th>来源</th><th>字段</th><th>值</th><th></th></tr></thead>
          <tbody>{(data.claims || []).map((c) => (
            <tr key={c.id}><td><span className="pill">{c.source}</span></td><td>{c.key}</td><td>{c.value} {c.unit}</td>
              <td><button className="btn ghost" onClick={async () => { await api("/api/claims?id=" + c.id, { method: "DELETE" }); load(); }}>删</button></td></tr>
          ))}</tbody></table></div>
      </div>
    </>
  );
}

function Compare() {
  const [data, setData] = useState({});
  useEffect(() => { api("/api/compare").then(setData); }, []);
  const keys = Object.keys(data);
  return (
    <div className="card">
      <h1>参数横评</h1>
      <p className="muted">同一字段下来自不同产品和来源的值并排，不覆盖。</p>
      {keys.length === 0 && <p>先在产品里记几条参数。</p>}
      {keys.map((k) => (
        <div key={k} style={{ marginBottom: "1rem" }}>
          <h2>{k}</h2>
          <div className="table-wrap"><table className="table"><thead><tr><th>产品</th><th>来源</th><th>值</th></tr></thead>
            <tbody>{data[k].map((c, i) => <tr key={i}><td>{c.product}</td><td>{c.source}</td><td>{c.value} {c.unit}</td></tr>)}</tbody></table></div>
        </div>
      ))}
    </div>
  );
}

function Machine() {
  const [d, setD] = useState(null);
  const [msg, setMsg] = useState("");
  const load = () => api("/api/machine").then(setD);
  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, []);
  useEffect(() => {
    if (!d?.ezviz?.configured) return;
    let dead = false;
    api("/api/camera").then((cam) => {
      if (dead || !window.EZUIKit) return;
      const el = document.getElementById("ezviz");
      if (!el) return;
      el.innerHTML = "";
      try {
        // eslint-disable-next-line no-undef
        new window.EZUIKit.EZUIKitPlayer({ id: "ezviz", accessToken: cam.accessToken, url: cam.url, width: el.clientWidth, height: 240 });
      } catch (e) { setMsg(String(e)); }
    }).catch((e) => setMsg(e.message));
    return () => { dead = true; };
  }, [d?.ezviz?.configured]);
  if (!d) return null;
  const b = d.bambu || {};
  const flip = async (role, on) => {
    try { await api("/api/actuators/" + role, { method: "POST", body: { on } }); setMsg("已发送"); } catch (e) { setMsg(e.message); }
  };
  return (
    <>
      <div className="card">
        <h1>机台（只读）</h1>
        <p className="muted">{b.connected ? <span className="ok">拓竹 MQTT 已连接</span> : <span>未连接。{b.error}</span>}</p>
        <div className="row cols-stats">
          <div>热床 <div className="stat">{b.bed_temp ?? "—"}</div><span className="muted">目标 {b.bed_target ?? "—"}</span></div>
          <div>喷嘴 <div className="stat">{b.nozzle_temp ?? "—"}</div><span className="muted">目标 {b.nozzle_target ?? "—"}</span></div>
          <div>进度 <div className="stat">{b.progress ?? "—"}%</div><span className="muted">{b.gcode_state || b.stage || "—"}</span></div>
        </div>
        <p>层数 {b.layer ?? "—"} / {b.total_layer ?? "—"}　剩余 {b.remaining ?? "—"} 分钟　{b.subtask || ""}</p>
      </div>
      <div className="card">
        <h2>监控 + 补光</h2>
        <div id="ezviz" />
        <p className="muted">萤石在设置页填 AppKey 后出画。同一页开补光。</p>
        <div className="sw"><span>补光灯</span><span><button className="btn ghost" onClick={() => flip("light", false)}>关</button> <button className="btn" onClick={() => flip("light", true)}>开</button></span></div>
      </div>
      <div className="card">
        <h2>净化器（易微联通断）</h2>
        <div className="sw"><span>仓内长开</span><span><button className="btn ghost" onClick={() => flip("box_always", false)}>关</button> <button className="btn" onClick={() => flip("box_always", true)}>开</button></span></div>
        <div className="sw"><span>仓内打印加强（打印中 + 结束后 30 分钟自动）</span><span><button className="btn ghost" onClick={() => flip("box_print", false)}>关</button> <button className="btn" onClick={() => flip("box_print", true)}>开</button></span></div>
        <div className="sw"><span>车间（有人自动）</span><span><button className="btn ghost" onClick={() => flip("room", false)}>关</button> <button className="btn" onClick={() => flip("room", true)}>开</button></span></div>
        {msg && <p className="muted">{msg}</p>}
      </div>
    </>
  );
}

function Air() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api("/api/air").then(setRows); const t = setInterval(() => api("/api/air").then(setRows), 8000); return () => clearInterval(t); }, []);
  const latest = rows[0];
  const pm = latest?.data?.pm25 ?? latest?.data?.room?.pm25;
  let band = "尚无数据";
  if (pm != null) {
    if (pm <= 35) band = "优";
    else if (pm <= 75) band = "良";
    else band = "超标倾向";
  }
  return (
    <div className="card">
      <h1>仓外空气</h1>
      <p>最新 PM2.5：<strong>{pm ?? "—"}</strong> µg/m³　参考色带 {band}</p>
      <p className="muted">对照 GB/T 18883 日均 50 µg/m³，仅供参考，非认证监测。仓内探头以后再加。</p>
      <div className="table-wrap"><table className="table"><thead><tr><th>时间</th><th>区</th><th>数据</th></tr></thead>
        <tbody>{rows.slice(0, 40).map((r, i) => (
          <tr key={i}><td>{new Date(r.ts * 1000).toLocaleString()}</td><td>{r.zone}</td><td><code>{JSON.stringify(r.data)}</code></td></tr>
        ))}</tbody></table></div>
    </div>
  );
}

function Settings() {
  const [s, setS] = useState(null);
  const [pw, setPw] = useState({ username: "", old_password: "", new_password: "" });
  const [msg, setMsg] = useState("");
  const [devs, setDevs] = useState([]);
  useEffect(() => { api("/api/settings").then(setS); api("/api/me").then((m) => setPw((p) => ({ ...p, username: m.username }))); }, []);
  if (!s) return null;
  const save = async () => {
    try { setS(await api("/api/settings", { method: "PUT", body: s })); setMsg("已保存，正在按新配置重连"); } catch (e) { setMsg(e.message); }
  };
  const patch = (group, key, val) => setS({ ...s, [group]: { ...s[group], [key]: val } });
  return (
    <>
      <div className="card">
        <h1>设置</h1>
        <p className="muted">拷给第二个人：跑起来后只在这一页填。密码框留空表示不改原值。</p>
        {msg && <p>{msg}</p>}
      </div>
      <div className="card">
        <h2>登录</h2>
        <div className="row cols-3">
          <label>站点名称<input value={s.site.title} onChange={(e) => patch("site", "title", e.target.value)} /></label>
          <label>用户名<input value={pw.username} onChange={(e) => setPw({ ...pw, username: e.target.value })} /></label>
          <label>原密码<input type="password" value={pw.old_password} onChange={(e) => setPw({ ...pw, old_password: e.target.value })} /></label>
        </div>
        <label>新密码<input type="password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></label>
        <p>
          <button className="btn" onClick={save}>保存站点名</button>{" "}
          <button className="btn ghost" onClick={async () => { await api("/api/settings/password", { method: "POST", body: pw }); setMsg("登录已更新"); }}>更新用户名密码</button>
        </p>
      </div>
      <div className="card">
        <h2>拓竹云（只读 MQTT）</h2>
        <div className="row cols-2">
          <label>地区<input value={s.bambu.region} onChange={(e) => patch("bambu", "region", e.target.value)} /></label>
          <label>打印机 SN<input value={s.bambu.printer_sn} onChange={(e) => patch("bambu", "printer_sn", e.target.value)} /></label>
          <label>账号<input value={s.bambu.account} onChange={(e) => patch("bambu", "account", e.target.value)} /></label>
          <label>密码<input type="password" placeholder="不改请留空" onChange={(e) => patch("bambu", "password", e.target.value)} /></label>
        </div>
        <p><button className="btn ghost" onClick={async () => { await save(); const r = await api("/api/settings/test/bambu", { method: "POST", body: {} }); setMsg(JSON.stringify(r)); }}>保存并测试拓竹</button></p>
      </div>
      <div className="card">
        <h2>易微联</h2>
        <div className="row cols-2">
          <label>地区<input value={s.ewelink.region} onChange={(e) => patch("ewelink", "region", e.target.value)} /></label>
          <label>手机或邮箱<input value={s.ewelink.account} onChange={(e) => patch("ewelink", "account", e.target.value)} /></label>
          <label>密码<input type="password" placeholder="不改请留空" onChange={(e) => patch("ewelink", "password", e.target.value)} /></label>
          <label>APPID（可空）<input value={s.ewelink.app_id} onChange={(e) => patch("ewelink", "app_id", e.target.value)} /></label>
          <label>APPSECRET（可空）<input type="password" placeholder="不改请留空" onChange={(e) => patch("ewelink", "app_secret", e.target.value)} /></label>
        </div>
        <p className="muted">四路填设备 ID。点测试可拉列表复制。</p>
        <div className="row cols-2">
          <label>补光灯 deviceid<input value={s.ewelink.light} onChange={(e) => patch("ewelink", "light", e.target.value)} /></label>
          <label>仓内长开<input value={s.ewelink.box_always} onChange={(e) => patch("ewelink", "box_always", e.target.value)} /></label>
          <label>仓内打印加强<input value={s.ewelink.box_print} onChange={(e) => patch("ewelink", "box_print", e.target.value)} /></label>
          <label>车间有人<input value={s.ewelink.room} onChange={(e) => patch("ewelink", "room", e.target.value)} /></label>
        </div>
        <label>打印结束后加强净化（分钟）<input type="number" value={s.automations.print_boost_minutes} onChange={(e) => setS({ ...s, automations: { ...s.automations, print_boost_minutes: Number(e.target.value) } })} /></label>
        <p>
          <button className="btn ghost" onClick={async () => { await save(); const r = await api("/api/settings/test/ewelink", { method: "POST", body: {} }); setDevs(r.devices || []); setMsg("易微联登录成功"); }}>保存并拉设备</button>
        </p>
        {devs.length > 0 && <div className="table-wrap"><table className="table"><thead><tr><th>名称</th><th>ID</th><th>在线</th></tr></thead>
          <tbody>{devs.map((d) => <tr key={d.id}><td>{d.name}</td><td><code>{d.id}</code></td><td>{d.online ? "是" : "否"}</td></tr>)}</tbody></table></div>}
      </div>
      <div className="card">
        <h2>萤石开放平台</h2>
        <div className="row cols-2">
          <label>AppKey<input value={s.ezviz.app_key} onChange={(e) => patch("ezviz", "app_key", e.target.value)} /></label>
          <label>AppSecret<input type="password" placeholder="不改请留空" onChange={(e) => patch("ezviz", "app_secret", e.target.value)} /></label>
          <label>设备序列号<input value={s.ezviz.device_serial} onChange={(e) => patch("ezviz", "device_serial", e.target.value)} /></label>
          <label>通道<input value={s.ezviz.channel} onChange={(e) => patch("ezviz", "channel", e.target.value)} /></label>
        </div>
        <p><button className="btn ghost" onClick={async () => { await save(); const r = await api("/api/settings/test/ezviz", { method: "POST", body: {} }); setMsg("萤石 token 长度 " + r.token_len); }}>保存并测试萤石</button></p>
      </div>
      <div className="card">
        <h2>空气探头</h2>
        <p>ESP32 上报地址：<code>POST /api/ingest/air</code></p>
        <label>Bearer 令牌<input value={s.air.token} onChange={(e) => patch("air", "token", e.target.value)} /></label>
        <p className="muted">留空再保存会自动生成。Header：Authorization: Bearer 令牌</p>
        <button className="btn" onClick={save}>保存全部设置</button>
      </div>
    </>
  );
}
