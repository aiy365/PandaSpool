
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_api = """async function api(path, req = null, opt = {}) {
  const h = { "Content-Type": "application/json" };
  const res = await fetch(path, {"""

new_api = """async function api(path, req = null, opt = {}) {
  const h = { "Content-Type": "application/json", "Cache-Control": "no-cache" };
  const p = path.includes("?") ? path + "&_=" + Date.now() : path + "?_=" + Date.now();
  const res = await fetch(p, {"""

text = text.replace(old_api, new_api)

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

