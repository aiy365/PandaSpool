
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("const air = d.air || {};\\n    if (document.querySelector(\\"[data-t]\\")) {", "if (document.querySelector(\\"[data-t]\\")) {")

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

