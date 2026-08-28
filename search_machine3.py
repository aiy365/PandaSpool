
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find("const b = d.bambu || {};")
print(text[max(0, idx-50):idx+800])

