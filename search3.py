
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

m = re.search(r"if \(.*?settings.*?\).*?\{", text)
if m:
    start = m.start()
    print(text[start:start+300])

