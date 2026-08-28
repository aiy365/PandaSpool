
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_speed = """    if (b.spd_lvl != null && String(b.spd_lvl) !== "2") {
        const lvlMap = {"1": "静音 50%", "3": "狂暴 124%", "4": "荒野狂飙 166%"};
        spdStr = `<span class="badge badge-secondary">${lvlMap[String(b.spd_lvl)] || "未知速度"}</span>`;
    }"""

new_speed = """    if (b.spd_lvl != null) {
        const spd = String(b.spd_lvl);
        if (spd === "1") spdStr = `<span class="badge badge-info">静音 50%</span>`;
        else if (spd === "2") spdStr = `<span class="badge badge-ghost">标准 100%</span>`;
        else if (spd === "3") spdStr = `<span class="badge badge-warning">运动 124%</span>`;
        else if (spd === "4") spdStr = `<span class="badge badge-error">狂暴 166%</span>`;
        else spdStr = `<span class="badge badge-secondary">未知速度 ${spd}</span>`;
    }"""

text = text.replace(old_speed, new_speed)

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

