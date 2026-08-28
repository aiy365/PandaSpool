
import re

with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("\"net/http\"", "\"net/http\"\n\t\"net/url\"")

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

