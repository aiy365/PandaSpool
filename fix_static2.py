
import re
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("\"io/fs\"\\n\\t\"net/http\"\\n\\t\"printpilot-hub/web\"\\n", "")
text = text.replace("import (", "import (\\n\\t\"io/fs\"\\n\\t\"printpilot-hub/web\"")
with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

