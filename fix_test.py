
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    content = f.read()

import re
old = r"go s.sendWebhookNotification\([^,]+, webhook, ppt, wxAT, wxUID, wcCorp, wcSec, wcAgent, wcTo, st\)"
new = r"go s.sendWebhookNotification(\"🔧 PrintPilot 连通性测试\", st)"
content = re.sub(old, new, content)

# Remove unused vars in testNotify
content = re.sub(r"cfg := s\.st\.LoadSettings\(\)\n.*?wcTo := cfg\.Automations\.WeComToUser\n\n", "", content, flags=re.DOTALL)

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(content)

