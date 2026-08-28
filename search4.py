
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()
import sys
for line in text.split("\n"):
    if "api(\"/api/settings" in line:
        print(line)

