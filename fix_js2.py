
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("\\`<tr>", "`<tr>")
text = text.replace("</tr>\\`", "</tr>`")

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

