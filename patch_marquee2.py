
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(r"// Elegant Title Marquee.*?\}\)\(\);\n", "", text, flags=re.DOTALL)

marquee_code = """
// Elegant Title Marquee (Hidden Beacon)
(function() {
  const originalTitle = "PrintPilot";
  const chars = Array.from("  ✦  PrintPilot  ✦  ");
  let interval;
  
  function startMarquee() {
    if (interval) return;
    interval = setInterval(() => {
      chars.push(chars.shift());
      let t = chars.join("");
      // prevent browser from trimming leading spaces
      if (t.startsWith(" ")) t = "\\u00A0" + t.substring(1);
      document.title = t;
    }, 400);
  }
  
  function stopMarquee() {
    clearInterval(interval);
    interval = null;
    document.title = originalTitle;
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      startMarquee();
    } else {
      stopMarquee();
    }
  });
})();
"""

text = marquee_code + "\n" + text
with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

