
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("""  let serverIp = "正在获取...";
  try { serverIp = await fetch("/api/server-ip").then(r => r.text()); } catch(e) {}""", """  let serverIp = "你的服务器公网IP";
  try { 
    let res = await fetch("/api/server-ip").then(r => r.text()); 
    if (res.trim() !== "") serverIp = res;
  } catch(e) {}""")

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

