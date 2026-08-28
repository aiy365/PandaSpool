
import re

with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

# Remove the old Elegant Marquee
text = re.sub(r"// Elegant Title Marquee.*?\}\)\(\);\n", "", text, flags=re.DOTALL)

useful_marquee = """
// Useful Marquee (Dynamic Printer Status in Title)
(function() {
  const originalTitle = "PrintPilot";
  let interval;
  
  async function updateTitle() {
    if (!document.hidden) return;
    try {
      const d = await api("/api/machine", { _noLoading: true }); // Assume standard fetch wrapper handles this or we just use raw fetch
      const b = d.bambu || {};
      if (!b.connected) {
        document.title = "⚠️ 打印机未连接";
        return;
      }
      if (d.printing) {
        const mins = parseInt(b.mc_remaining_time, 10);
        if (!isNaN(mins) && mins > 0) {
          const now = new Date();
          const end = new Date(now.getTime() + mins * 60000);
          const pad = (n) => n.toString().padStart(2, "0");
          const isNextDay = end.getDate() !== now.getDate();
          document.title = `⏳ 还有 ${mins<60 ? mins+"分钟" : Math.floor(mins/60)+"小时"+(mins%60)+"分"} (${isNextDay?"次日":""}${pad(end.getHours())}:${pad(end.getMinutes())})`;
        } else {
          document.title = "🔥 打印中...";
        }
      } else {
        document.title = "🟢 打印机空闲";
      }
    } catch(e) {
      document.title = "❓ 状态未知";
    }
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      updateTitle();
      interval = setInterval(updateTitle, 30000); // Check every 30 seconds when hidden
    } else {
      if (interval) clearInterval(interval);
      interval = null;
      document.title = originalTitle;
    }
  });
})();
"""

text = useful_marquee + "\n" + text
with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

