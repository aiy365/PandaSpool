import re

with open('live_app.js', 'r', encoding='utf-8') as f:
    js = f.read()

old_save_st = """await api("/api/settings", { method: "POST", body: payload });
      toast("保存成功", "success");"""
new_save_st = """await api("/api/settings", { method: "POST", body: payload });
      toast("保存成功", "success");
      updateAppTitle(payload.site.title);"""
if "updateAppTitle(payload.site.title);" not in js:
    js = js.replace(old_save_st, new_save_st)

with open('live_app.js', 'w', encoding='utf-8') as f:
    f.write(js)
