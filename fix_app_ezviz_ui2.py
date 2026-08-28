
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_fields = """        ${field("通道", inputEl("zc", `value="${esc(s.ezviz.channel)}"`))}
        ${field("画面旋转", `<select id="zr" class="select select-bordered w-full">
          <option value="" ${!s.ezviz.rotation || s.ezviz.rotation === "" || s.ezviz.rotation === "0" ? "selected" : ""}>正常</option>
          <option value="90" ${s.ezviz.rotation === "90" ? "selected" : ""}>向右旋转 90°</option>
          <option value="-90" ${s.ezviz.rotation === "-90" ? "selected" : ""}>向左旋转 90°</option>
          <option value="180" ${s.ezviz.rotation === "180" ? "selected" : ""}>旋转 180°</option>
        </select>`)}
      </div>"""

new_fields = """        ${field("通道", inputEl("zc", `value="${esc(s.ezviz.channel)}"`))}
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
      </div>"""

text = text.replace(old_fields, new_fields)

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

