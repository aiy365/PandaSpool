
with open("README.md", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("docs/bom.md", "docs/PrintPilot缝合体_实用主义BOM_v3.md")

with open("README.md", "w", encoding="utf-8") as f:
    f.write(text)

