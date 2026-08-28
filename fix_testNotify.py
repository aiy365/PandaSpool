
import re

with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

text = re.sub(r"func \(s \*Server\) applyIntegrations\(\) \{.*", "", text, flags=re.DOTALL)
text += """func (s *Server) applyIntegrations() {
	cfg := s.st.LoadSettings()
	webhook := cfg.Automations.LarkWebhook
	ppt := cfg.Automations.PushPlusToken
	wxAT := cfg.Automations.WxPusherAppToken
	wxUID := cfg.Automations.WxPusherUID
	wcCorp := cfg.Automations.WeComCorpID
	wcSec := cfg.Automations.WeComSecret
	wcAgent := cfg.Automations.WeComAgentID
	wcTo := cfg.Automations.WeComToUser

	st := s.bambu.Status()
	if st["gcode_state"] == nil {
		st["gcode_state"] = "TEST_RUNNING"
		st["layer"] = 99
		st["total_layer"] = 100
	}

	go s.sendWebhookNotification("🔧 PrintPilot 连通性测试", st)
}

func (s *Server) testNotify(w http.ResponseWriter, r *http.Request) {
	st := s.bambu.Status()
	if st["gcode_state"] == nil {
		st["gcode_state"] = "TEST_RUNNING"
		st["layer"] = 99
		st["total_layer"] = 100
	}

	go s.sendWebhookNotification("🔧 PrintPilot 连通性测试", st)
	w.Write([]byte(`{"status":"ok"}`))
}
"""

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

