
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_stop = """            $("#ezviz").innerHTML = "";
          }
        };"""

new_stop = """            $("#ezviz").innerHTML = "";
            $("#ezviz").style.height = "";
          }
        };"""

text = text.replace(old_stop, new_stop)

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

