
import re

with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("import (\n\t\"io/fs\"", "import (\n\t\"io\"\n\t\"io/fs\"")

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

