
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("return card(\\`<h2", "return card(`<h2")
text = text.replace("</table></div>\\`);", "</table></div>`);")
text = text.replace("\\${", "${")

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

