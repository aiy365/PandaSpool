
import re
with open("internal/server/notify.go", "r", encoding="utf-8") as f:
    text = f.read()

old_block = """									"title":       title,
									"description": desc,
									"url":         "https://3d.bstccc.cn/#/machine",
									"picurl":      picUrl,"""

new_block = """									"title":       title,
									"description": desc,
									"url":         picUrl,
									"picurl":      picUrl,"""

text = text.replace(old_block, new_block)

with open("internal/server/notify.go", "w", encoding="utf-8") as f:
    f.write(text)

