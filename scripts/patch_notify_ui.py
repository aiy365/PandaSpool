import io

p = 'web/live_app.js'
src = io.open(p, encoding='utf-8').read()

# A. updateAppTitle 指到真实的顶栏品牌元素
old_a = '''function updateAppTitle(title) {
  const displayTitle = title || "PandaSpool";
  document.title = displayTitle;
  const brandEl = document.querySelector(".navbar-center .btn-ghost");
  if (brandEl) brandEl.innerText = displayTitle;
  const brandMobileEl = document.querySelector(".drawer-side .text-2xl");
  if (brandMobileEl) brandMobileEl.innerText = displayTitle;
}'''
new_a = '''function updateAppTitle(title) {
  const displayTitle = title || "PandaSpool";
  document.title = displayTitle;
  const brandEl = document.getElementById("brand");
  if (brandEl) brandEl.innerText = displayTitle;
}'''
assert old_a in src, 'A not found'
src = src.replace(old_a, new_a)

# B. 顶栏品牌元素挂 id
old_b = '<span class="btn btn-ghost text-lg text-primary">${esc(me.title || "PandaSpool")}</span>'
new_b = '<span class="btn btn-ghost text-lg text-primary" id="brand">${esc(me.title || "PandaSpool")}</span>'
assert old_b in src, 'B not found'
src = src.replace(old_b, new_b)

# C. saveSite 用 toast + 即时刷新品牌；保存通知设置 = 保存 + 企业微信凭证验证反馈
old_c = '''  const saveSite = async () => {
    await api("/api/settings", { method: "PUT", body: collect() });
    alert("保存成功!");
  };
  $("#testwh")?.addEventListener("click", async (e) => {
    busy(e.currentTarget, async () => {
      await api("/api/notify/test", { method: "POST" });
      alert("测试推送指令已下发！请去手机上查看是否收到通知。\\n注意：需要先点击左侧的【保存通知设置】！");
    }, "send");
  });'''
new_c = '''  const saveSite = async () => {
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
  }, "set");'''
assert old_c in src, 'C not found'
src = src.replace(old_c, new_c)

# D. getColorName 换成 HSL 色相命名（16 色板把紫色判成浅灰）
i = src.index('const getColorName = (hex) => {')
marker = 'return closest;'
j = src.index(marker, i) + len(marker)
# 吃掉其后的 "\n        };"
if src[j:j+12].startswith(';\n        };'):
    j += len(';\n        };')
elif src[j:j+2] == ';\n':
    k = src.index('};', j)
    j = k + 2
new_gcn = '''const getColorName = (hex) => {
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
        };'''
src = src[:i] + new_gcn + src[j:]

io.open(p, 'w', encoding='utf-8', newline='\n').write(src)
print('patched OK')
