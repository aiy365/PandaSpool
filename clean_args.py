
import re

with open("internal/server/notify.go", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the signature and function definition
content = re.sub(
    r"func \(s \*Server\) sendWebhookNotification\(.*?\)\s*\{",
    r"func (s *Server) sendWebhookNotification(title string, st map[string]any) {",
    content
)

# Remove the arguments passed in tickNotifications
content = re.sub(
    r"go s\.sendWebhookNotification\(([^,]+).*?st\)",
    r"go s.sendWebhookNotification(\1, st)",
    content
)

# In tickNotifications, we don"t need to read all config if we don"t use them, but let"s just let go build complain if they are unused.
# Let"s just do a blind replace of the old tickNotifications variables.
old_vars = """	webhook := cfg.Automations.LarkWebhook
	ppt := cfg.Automations.PushPlusToken
	wxAT := cfg.Automations.WxPusherAppToken
	wxUID := cfg.Automations.WxPusherUID
	wcCorp := cfg.Automations.WeComCorpID
	wcSec := cfg.Automations.WeComSecret
	wcAgent := cfg.Automations.WeComAgentID
	wcTo := cfg.Automations.WeComToUser
	if webhook == "" && ppt == "" && (wxAT == "" || wxUID == "") && (wcCorp == "" || wcSec == "") {
		return
	}"""
new_vars = """	wcCorp := cfg.Automations.WeComCorpID
	wcSec := cfg.Automations.WeComSecret
	if wcCorp == "" || wcSec == "" {
		return
	}"""
content = content.replace(old_vars, new_vars)

with open("internal/server/notify.go", "w", encoding="utf-8") as f:
    f.write(content)

