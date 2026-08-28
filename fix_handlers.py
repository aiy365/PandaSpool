
code = """
func (s *Server) summary(w http.ResponseWriter, r *http.Request) {
	json.NewEncoder(w).Encode(s.st.Summary())
}

func (s *Server) settings(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		json.NewEncoder(w).Encode(s.st.LoadSettings())
		return
	}
	var cfg store.Settings
	if err := json.NewDecoder(r.Body).Decode(&cfg); err == nil {
		s.st.SaveSettings(cfg)
		s.applyIntegrations()
	}
	w.Write([]byte(`{"status":"ok"}`))
}

func (s *Server) changePassword(w http.ResponseWriter, r *http.Request) {
	var req struct { Password string `json:"password"` }
	json.NewDecoder(r.Body).Decode(&req)
	s.st.SetAdmin(s.st.AdminUsername(), req.Password)
	w.Write([]byte(`{"status":"ok"}`))
}

func (s *Server) testBambu(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) bambuSendCode(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) bambuVerifyCode(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) bambuToken(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) testEWeLink(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) testEzviz(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
"""

with open("internal/server/server.go", "a", encoding="utf-8") as f:
    f.write("\n" + code)

