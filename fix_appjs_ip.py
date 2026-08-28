
import re

with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

# I will replace the static strings with a span that gets filled.
text = text.replace("""<code>https://3d.bstccc.cn/api/wecom/verify</code>""", """<code id="wecom-webhook-url">https://.../api/wecom/verify</code>""")
text = text.replace("""<code>159.75.227.95</code>""", """<code id="wecom-server-ip">获取中...</code>""")

# Now add logic to fill these on render.
# Look for the settings tab click or render block.
render_block = """  if (hash === "#/settings") {
    let s = await api("/api/settings");
    $("#page").innerHTML = `
      <div class="card p-3 mb-3 max-w-lg">"""

new_render_block = """  if (hash === "#/settings") {
    let s = await api("/api/settings");
    let serverIp = "获取失败";
    try { serverIp = await fetch("/api/server-ip").then(r => r.text()); } catch(e) {}
    let hookUrl = window.location.protocol + "//" + window.location.host + "/api/wecom/verify";

    $("#page").innerHTML = `
      <div class="card p-3 mb-3 max-w-lg">"""

text = text.replace(render_block, new_render_block)
text = text.replace("""<code id="wecom-webhook-url">https://.../api/wecom/verify</code>""", """<code id="wecom-webhook-url">${hookUrl}</code>""")
text = text.replace("""<code id="wecom-server-ip">获取中...</code>""", """<code id="wecom-server-ip">${serverIp}</code>""")

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

