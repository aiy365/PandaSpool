
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("\"io\"", "")
text = text.replace("\"printpilot-hub/web\"", "")

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

