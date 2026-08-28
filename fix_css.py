
import re
with open("web/dist/styles.css", "r", encoding="utf-8") as f:
    text = f.read()
text = re.sub(r"\.inv-list\s*\{[^}]*\}", "", text)
with open("web/dist/styles.css", "w", encoding="utf-8") as f:
    f.write(text)

