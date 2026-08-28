
import re
with open("web/dist/styles.css", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    ".page-wide { max-width: 1280px; }",
    ".page-wide { max-width: 1800px; }"
)

text = text.replace(
    ".inv-list { display: grid; gap: .75rem; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }",
    ".inv-list { display: grid; gap: .75rem; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }"
)

with open("web/dist/styles.css", "w", encoding="utf-8") as f:
    f.write(text)

