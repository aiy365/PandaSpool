
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()
    idx = text.find("async function viewStock(")
    print(text[idx+1000:idx+2500])

