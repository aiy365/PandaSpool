import re

with open('live_app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the mqtt badge for unconnected
old_mqtt = '`<span class="badge badge-ghost">未连接拓竹，去设置页填写</span>`'
new_mqtt = '`<a href="#/settings" class="badge badge-ghost hover:badge-primary cursor-pointer">未连接拓竹，点击去设置页填写</a>`'
content = content.replace(old_mqtt, new_mqtt)

# Replace Machine and Air Card in viewHome
old_home_cards = """    ${card(`
      <h2 class="card-title">机台</h2>
      <p>${mqtt} ${printing ? `<span class="badge badge-success">打印中 ${m.progress ?? "—"}%</span>` : `<span class="badge badge-ghost">${esc(m.gcode_state || m.stage || "空闲")}</span>`} ${boost}</p>
      <p>${printing ? `${esc(job || "正在打印")}　剩余 ${esc(remain)} 分钟` : `热床 ${m.bed_temp ?? "—"}　喷嘴 ${m.nozzle_temp ?? "—"}`}</p>
      <p class="muted">${printing ? `热床 ${m.bed_temp ?? "—"}　喷嘴 ${m.nozzle_temp ?? "—"}　层 ${m.layer ?? "—"}/${m.total_layer ?? "—"}` : esc(job)}</p>
      <div class="card-actions"><a class="btn btn-sm btn-primary" href="#/machine">打开机台页</a></div>
    `)}
    ${card(`
      <h2 class="card-title">空气</h2>
      <p>PM2.5 <strong>${air.pm25 ?? "—"}</strong> µg/m³　室温 ${air.t_c ?? "—"} ℃　湿度 ${air.rh ?? "—"} %</p>
      <p class="${airStale ? "text-warning" : "muted"}">${air.ts ? `探头 ${esc(airAge || "")}${airStale ? " · 超过 15 分钟没报" : ""}` : "还没有探头数据"}　有人 ${air.presence ?? "—"}</p>
      <div class="card-actions"><a class="btn btn-sm btn-ghost" href="#/air">空气记录</a><a class="btn btn-sm btn-ghost" href="#/stock">架子盘点</a></div>
    `)}"""

new_home_cards = """    ${card(`
      <h2 class="card-title">机台</h2>
      <p class="mb-2">${mqtt} ${m.connected ? (printing ? `<span class="badge badge-success">打印中 ${m.progress ?? "—"}%</span>` : `<span class="badge badge-ghost">${esc(m.gcode_state || m.stage || "空闲")}</span>`) : ""} ${boost}</p>
      ${m.connected ? `
        <p>${printing ? `${esc(job || "正在打印")}　剩余 ${esc(remain)} 分钟` : `热床 ${m.bed_temp ?? "—"}°C　喷嘴 ${m.nozzle_temp ?? "—"}°C`}</p>
        <p class="muted">${printing ? `热床 ${m.bed_temp ?? "—"}°C　喷嘴 ${m.nozzle_temp ?? "—"}°C　层 ${m.layer ?? "—"}/${m.total_layer ?? "—"}` : esc(job)}</p>
      ` : `
        <div class="py-2 text-center text-sm muted bg-base-200 rounded-box my-2">机器未连接，无法读取温度或任务状态。</div>
      `}
      <div class="card-actions mt-2"><a class="btn btn-sm btn-primary" href="#/machine">打开机台页</a></div>
    `)}
    ${card(`
      <h2 class="card-title">空气</h2>
      ${air.ts ? `
        <p>PM2.5 <strong>${air.pm25 ?? "—"}</strong> µg/m³　室温 ${air.t_c ?? "—"} ℃　湿度 ${air.rh ?? "—"} %</p>
        <p class="${airStale ? "text-warning" : "muted"} mt-2">探头 ${esc(airAge || "")}${airStale ? " · 超过 15 分钟没报" : ""}　有人 ${air.presence ?? "—"}</p>
      ` : `
        <div class="py-2 text-center text-sm muted bg-base-200 rounded-box my-2">尚未接入环境探头，无空气数据。</div>
      `}
      <div class="card-actions mt-2"><a class="btn btn-sm btn-ghost" href="#/air">空气记录</a><a class="btn btn-sm btn-ghost" href="#/stock">架子盘点</a></div>
    `)}"""

content = content.replace(old_home_cards, new_home_cards)

with open('live_app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated viewHome cards.")
