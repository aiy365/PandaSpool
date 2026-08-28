
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_fields = """        ${field("Secret", inputEl("zs", `type="password" placeholder="不改请留空"`))}
        ${field("设备序列号", inputEl("zd", `value="${esc(s.ezviz.device_serial)}"`))}
        ${field("通道", inputEl("zc", `value="${esc(s.ezviz.channel)}"`))}
      </div>"""

new_fields = """        ${field("Secret", inputEl("zs", `type="password" placeholder="不改请留空"`))}
        ${field("设备序列号", inputEl("zd", `value="${esc(s.ezviz.device_serial)}"`))}
        ${field("通道", inputEl("zc", `value="${esc(s.ezviz.channel)}"`))}
        ${field("画面旋转", `<select id="zr" class="select select-bordered w-full">
          <option value="" ${!s.ezviz.rotation || s.ezviz.rotation === "" || s.ezviz.rotation === "0" ? "selected" : ""}>正常</option>
          <option value="90" ${s.ezviz.rotation === "90" ? "selected" : ""}>向右旋转 90°</option>
          <option value="-90" ${s.ezviz.rotation === "-90" ? "selected" : ""}>向左旋转 90°</option>
          <option value="180" ${s.ezviz.rotation === "180" ? "selected" : ""}>旋转 180°</option>
        </select>`)}
      </div>"""

text = text.replace(old_fields, new_fields)

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

