
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

text = re.sub(r"""<div class="font-bold">微信推送 \(WxPusher - 免费无限制\).*?</div>\s*</div>""", "", text, flags=re.DOTALL)

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

