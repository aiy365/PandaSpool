
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_stats = """      <div class="stats stats-vertical lg:stats-horizontal shadow-sm bg-base-200 w-full">
        <div class="stat"><div class="stat-title">热床</div><div class="stat-value text-primary">${b.bed_temp ?? "—"}</div><div class="stat-desc">目标 ${b.bed_target ?? "—"}</div></div>
        <div class="stat"><div class="stat-title">喷嘴</div><div class="stat-value">${b.nozzle_temp ?? "—"}</div><div class="stat-desc">目标 ${b.nozzle_target ?? "—"}</div></div>
        <div class="stat"><div class="stat-title">进度</div><div class="stat-value">${b.progress ?? "—"}%</div><div class="stat-desc">剩余 ${b.remaining ?? "—"} 分钟</div></div>
      </div>"""

new_stats = """      ${(() => {
          const formatTemp = (t) => t != null ? Math.round(Number(t)) : "—";
          const formatTime = (mins) => {
              if (mins == null) return "—";
              const m = parseInt(mins, 10);
              if (isNaN(m)) return "—";
              if (m < 60) return `${m} 分钟`;
              return `${Math.floor(m/60)}小时${m%60}分钟`;
          };
          const calcEnd = (mins) => {
              if (mins == null) return "";
              const m = parseInt(mins, 10);
              if (isNaN(m) || m <= 0) return "";
              const now = new Date();
              const end = new Date(now.getTime() + m * 60000);
              const pad = (n) => n.toString().padStart(2, "0");
              const isNextDay = end.getDate() !== now.getDate();
              return `<div class="mt-1 text-xs opacity-70">预计 ${isNextDay ? "次日 " : ""}${pad(end.getHours())}:${pad(end.getMinutes())} 结束</div>`;
          };
          return `
      <div class="stats stats-vertical lg:stats-horizontal shadow-sm bg-base-200 w-full">
        <div class="stat">
          <div class="stat-title">热床</div>
          <div class="stat-value text-primary">${formatTemp(b.bed_temp)}<span class="text-lg">°C</span></div>
          <div class="stat-desc">目标 ${formatTemp(b.bed_target)}°C</div>
        </div>
        <div class="stat">
          <div class="stat-title">喷嘴</div>
          <div class="stat-value">${formatTemp(b.nozzle_temp)}<span class="text-lg">°C</span></div>
          <div class="stat-desc">目标 ${formatTemp(b.nozzle_target)}°C</div>
        </div>
        <div class="stat">
          <div class="stat-title">进度</div>
          <div class="stat-value">${b.progress ?? "—"}%</div>
          <div class="stat-desc">剩余 ${formatTime(b.remaining)}${calcEnd(b.remaining)}</div>
        </div>
      </div>`;
      })()}"""

text = text.replace(old_stats, new_stats)

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

