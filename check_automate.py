
import re
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

m = re.search(r"func \(s \*Server\) automate\(\) \{.+?\}", text, re.DOTALL)
if m:
    print(m.group(0)[:1000])
else:
    print("Not found")

