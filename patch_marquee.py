
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

marquee_code = """
// Elegant Title Marquee
(function() {
  const chars = Array.from("  ✦  PrintPilot Hub  ✦  ");
  setInterval(() => {
    chars.push(chars.shift());
    document.title = chars.join("").replace(/^\s/, "\\u00A0");
  }, 400);
})();
"""

if "Elegant Title Marquee" not in text:
    text = marquee_code + "\n" + text
    with open("web/dist/app.js", "w", encoding="utf-8") as f:
        f.write(text)

