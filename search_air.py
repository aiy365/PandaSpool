
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find("await api(\"/api/air\")")
if idx != -1:
    print(text[max(0, idx-100):idx+500])

