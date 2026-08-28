
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()
print("Backticks:", text.count("`"))

