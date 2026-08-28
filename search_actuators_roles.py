
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()
import sys
for i, line in enumerate(text.split("\n")):
    if "data-a=\"${role}\"" in line:
        print("\n".join(text.split("\n")[max(0, i-10):i+5]))

