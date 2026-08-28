
import re

with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

text = re.sub(r"// Useful Marquee.*?\}\)\(\);\n", "", text, flags=re.DOTALL)

useful_marquee = """
// Scrolling Useful Marquee (Dynamic Printer Status)
(function() {
  const originalTitle = "PrintPilot";
  let fetchInterval, scrollInterval;
  let statusText = " PrintPilot ";
  let chars = Array.from(statusText + " ✦ ");

  async function fetchStatus() {
    if (!document.hidden) return;
    try {
      const d = await api("/api/machine", { _noLoading: true });
      const b = d.bambu || {};
      if (!b.connected) {
        statusText = "⚠️ 打印机未连接";
      } else if (d.printing) {
        const mins = parseInt(b.remaining, 10);
        const prog = parseInt(b.progress, 10);
        let progStr = isNaN(prog) ? "" : ` 进度 ${prog}%`;
        if (!isNaN(mins) && mins > 0) {
          const now = new Date();
          const end = new Date(now.getTime() + mins * 60000);
          const pad = (n) => n.toString().padStart(2, "0");
          const isNextDay = end.getDate() !== now.getDate();
          statusText = `⏳ 打印中${progStr} · 剩余 ${mins<60 ? mins+"分钟" : Math.floor(mins/60)+"小时"+(mins%60)+"分"} (预计 ${isNextDay?"次日":""}${pad(end.getHours())}:${pad(end.getMinutes())} 结束)`;
        } else {
          statusText = `🔥 打印中${progStr}...`;
        }
      } else {
        statusText = "🟢 打印机空闲";
      }
    } catch(e) {
      statusText = "❓ 状态未知";
    }
    
    // Update the scroll array if the text changed
    const newStr = " " + statusText + " ✦ ";
    if (chars.join("") !== newStr && chars.length === Array.from(newStr).length) {
      // It might be scrolling, so we don`t want to hard reset the array if we don`t have to,
      // but actually it`s easier to just reset the array
      chars = Array.from(newStr);
    } else if (chars.join("").indexOf(statusText) === -1) {
      chars = Array.from(newStr);
    }
  }

  function scrollTitle() {
    chars.push(chars.shift());
    let t = chars.join("");
    if (t.startsWith(" ")) t = "\\u00A0" + t.substring(1);
    document.title = t;
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      fetchStatus();
      fetchInterval = setInterval(fetchStatus, 30000); // Fetch data every 30s
      scrollInterval = setInterval(scrollTitle, 400);  // Scroll every 400ms
    } else {
      clearInterval(fetchInterval);
      clearInterval(scrollInterval);
      fetchInterval = null;
      scrollInterval = null;
      document.title = originalTitle;
    }
  });
})();
"""

text = useful_marquee + "\n" + text
with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

