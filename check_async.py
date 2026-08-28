
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

m = re.search(r".{0,100}function viewSettings.{0,200}", text, re.DOTALL)
if m:
    print(m.group(0))

