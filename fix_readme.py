
import re

with open("README.md", "r", encoding="utf-8") as f:
    text = f.read()

# Fix the BOM reference
text = text.replace("见仓库文档 `docs/` 里的仓外低成本 BOM。", "见仓库文档 `docs/bom.md` 里的硬件部署方案与 BOM 表。")

with open("README.md", "w", encoding="utf-8") as f:
    f.write(text)
print("README.md updated.")

