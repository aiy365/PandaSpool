
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find("swRow(")
if idx != -1:
    idx = text.find("swRow(", idx+10)
    print(text[max(0, idx-100):idx+500])

