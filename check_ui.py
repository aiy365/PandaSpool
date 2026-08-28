
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

import re
print("--- viewMachine ---")
match = re.search(r"function viewMachine\(\) \{.+?setInterval", text, flags=re.DOTALL)
if match: print(match.group(0)[:1500])

print("--- viewSettings ---")
match = re.search(r"function viewSettings\(\) \{.+?\}", text, flags=re.DOTALL)
if match: print(match.group(0)[:1500])

