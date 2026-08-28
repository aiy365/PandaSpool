
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()
    idx = text.find("function productCost")
    print(text[idx:idx+500])

