
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_ezviz_collect = """ezviz: { app_key: $("#zk").value, app_secret: $("#zs").value, device_serial: $("#zd").value, channel: $("#zc").value, rotation: $("#zr")?.value || "" },"""
new_ezviz_collect = """ezviz: { app_key: $("#zk").value, app_secret: $("#zs").value, device_serial: $("#zd").value, channel: $("#zc").value, rotation: $("#zr")?.value || "", crop: `${$("#zc_t")?.value||0},${$("#zc_b")?.value||0},${$("#zc_l")?.value||0},${$("#zc_r")?.value||0}` },"""
text = text.replace(old_ezviz_collect, new_ezviz_collect)

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

