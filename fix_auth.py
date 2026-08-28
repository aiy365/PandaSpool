
import re

with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

text = re.sub(r"func \(s \*Server\) login.*?\n\}", """func (s *Server) login(w http.ResponseWriter, r *http.Request) {
	var req struct { Password string `json:"password"` }
	json.NewDecoder(r.Body).Decode(&req)
	if s.st.CheckAdmin(s.st.AdminUsername(), req.Password) {
		http.SetCookie(w, &http.Cookie{Name: "token", Value: "admin", Path: "/", MaxAge: 86400 * 30})
		w.Write([]byte(`{"status":"ok"}`))
	} else {
		w.WriteHeader(401)
	}
}""", text, flags=re.DOTALL)

text = re.sub(r"func \(s \*Server\) setup.*?\n\}", """func (s *Server) setup(w http.ResponseWriter, r *http.Request) {
	var req struct { Password string `json:"password"` }
	json.NewDecoder(r.Body).Decode(&req)
	if !s.st.HasAdmin() {
		s.st.SetAdmin("admin", req.Password)
	}
	w.Write([]byte(`{"status":"ok"}`))
}""", text, flags=re.DOTALL)

text = re.sub(r"func \(s \*Server\) bootstrap.*?\n\}", """func (s *Server) bootstrap(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte(`{"ready":` + fmt.Sprintf("%v", s.st.HasAdmin()) + `}`))
}""", text, flags=re.DOTALL)

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

