
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()
    idx = text.find("按材料")
    print(text[max(0, idx-500):idx+1500])

