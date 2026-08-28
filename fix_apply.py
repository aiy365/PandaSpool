
import re
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

apply_code = """
func (s *Server) applyIntegrations() {
	cfg := s.st.LoadSettings()
	s.ezviz.AppKey = cfg.Ezviz.AppKey
	s.ezviz.AppSecret = cfg.Ezviz.AppSecret
	s.ezviz.DeviceSerial = cfg.Ezviz.DeviceSerial
}
"""
text = text.replace("func (s *Server) testNotify", apply_code + "\nfunc (s *Server) testNotify")
with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

