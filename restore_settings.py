
import re

with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

# Replace the grid wrapper
text = text.replace("<div class=\"grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 items-start\">", "<div class=\"settings-grid\">")

# Add the wrappers around the cards
text = text.replace("${card(`\\n      <h2 class=\"card-title\">登录</h2>", "<div class=\"settings-login\">${card(`\\n      <h2 class=\"card-title\">登录</h2>")
text = text.replace("</button>\\n      </div>\\n    `)}", "</button>\\n      </div>\\n    `)}</div>")

text = text.replace("${card(`\\n      <h2 class=\"card-title\">拓竹云（只读）</h2>", "<div class=\"settings-bambu\">${card(`\\n      <h2 class=\"card-title\">拓竹云（只读）</h2>")
text = text.replace("用 Token 登录</button>\\n      </div>\\n    `)}", "用 Token 登录</button>\\n      </div>\\n    `)}</div>")

text = text.replace("${card(`\\n      <h2 class=\"card-title\">易微联</h2>", "<div class=\"settings-ew\">${card(`\\n      <h2 class=\"card-title\">易微联</h2>")
text = text.replace("<div id=\"elist\"></div>\\n    `)}", "<div id=\"elist\"></div>\\n    `)}</div>")

text = text.replace("${card(`\\n      <h2 class=\"card-title\">萤石</h2>", "<div class=\"settings-ez\">${card(`\\n      <h2 class=\"card-title\">萤石</h2>")
text = text.replace("保存并测试萤石</button></div>\\n    `)}", "保存并测试萤石</button></div>\\n    `)}</div>")

text = text.replace("${card(`\\n      <h2 class=\"card-title\">消息通知</h2>", "<div class=\"settings-air\">${card(`\\n      <h2 class=\"card-title\">消息通知</h2>")
text = text.replace("</div>\\n    `)}\\n  `;", "</div>\\n    `)}</div>\\n  `;")

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

