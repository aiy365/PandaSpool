
import re

with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

# Fix applyIntegrations
text = text.replace("s.ez.AppKey = cfg.Ezviz.AppKey", "s.ez.Configure(cfg.Ezviz.AppKey, cfg.Ezviz.AppSecret)")
text = text.replace("s.ez.AppSecret = cfg.Ezviz.AppSecret\n", "")
text = text.replace("s.ez.DeviceSerial = cfg.Ezviz.DeviceSerial\n", "")

missing = """
func (s *Server) login(w http.ResponseWriter, r *http.Request) {
	var req struct { Password string `json:"password"` }
	json.NewDecoder(r.Body).Decode(&req)
	if s.st.CheckAdmin(s.st.AdminUsername(), req.Password) {
		http.SetCookie(w, &http.Cookie{Name: "token", Value: "admin", Path: "/", MaxAge: 86400 * 30})
		w.Write([]byte(`{"status":"ok"}`))
	} else {
		w.WriteHeader(401)
	}
}

func (s *Server) automate() {}
func withLog(h http.Handler) http.Handler { return h }
"""
with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text + "\n" + missing)

