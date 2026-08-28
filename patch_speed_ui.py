
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_ui = """    const boost = b.print_boost_active ? `<span class="badge badge-warning">打印加强开着</span>` : "";
    $("#mach-stats").innerHTML = `
      <p>${b.connected ? '<span class="badge badge-success">拓竹 MQTT 已连接</span>' : `<span class="badge badge-error badge-outline">未连接</span> <span class="muted">${esc(b.error || "")}</span>`}
        ${printing ? `<span class="badge badge-success">打印中</span>` : `<span class="badge badge-ghost">${esc(b.gcode_state || b.stage || "空闲")}</span>`}
        ${boost}</p>"""

new_ui = """    const boost = b.print_boost_active ? `<span class="badge badge-warning">打印加强开着</span>` : "";
    let spdStr = "";
    if (b.spd_lvl != null && String(b.spd_lvl) !== "2") {
        const lvlMap = {"1": "静音 50%", "3": "狂暴 124%", "4": "荒野狂飙 166%"};
        spdStr = `<span class="badge badge-secondary">${lvlMap[String(b.spd_lvl)] || "未知速度"}</span>`;
    }
    $("#mach-stats").innerHTML = `
      <p>${b.connected ? '<span class="badge badge-success">拓竹 MQTT 已连接</span>' : `<span class="badge badge-error badge-outline">未连接</span> <span class="muted">${esc(b.error || "")}</span>`}
        ${printing ? `<span class="badge badge-success">打印中</span>` : `<span class="badge badge-ghost">${esc(b.gcode_state || b.stage || "空闲")}</span>`}
        ${boost} ${spdStr}</p>"""

text = text.replace(old_ui, new_ui)

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

