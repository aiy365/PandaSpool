
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_func = """async function viewSettings(me) {
  $("#page").classList.add("page-wide");
  pageLoading("正在打开设置…");
  let s;
  try { s = await api("/api/settings"); }
  catch (ex) { pageError(ex); return; }"""

new_func = """async function viewSettings(me) {
  $("#page").classList.add("page-wide");
  pageLoading("正在打开设置…");
  let s;
  try { s = await api("/api/settings"); }
  catch (ex) { pageError(ex); return; }
  
  let hookUrl = window.location.protocol + "//" + window.location.host + "/api/wecom/verify";
  let serverIp = "正在获取...";
  try { serverIp = await fetch("/api/server-ip").then(r => r.text()); } catch(e) {}
"""

text = text.replace(old_func, new_func)

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

