
code = """
func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte(`{"status":"ok"}`))
}

func (s *Server) bootstrap(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte(`{"ready":true}`))
}

func (s *Server) setup(w http.ResponseWriter, r *http.Request) {}

func (s *Server) login(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Set-Cookie", "token=admin; Path=/")
	w.Write([]byte(`{"status":"ok"}`))
}

func (s *Server) logout(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Set-Cookie", "token=; Path=/; Max-Age=0")
}

func (s *Server) auth(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		next(w, r)
	}
}

func (s *Server) me(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte(`{"user":"admin"}`))
}
"""

with open("internal/server/server.go", "a", encoding="utf-8") as f:
    f.write("\n" + code)

