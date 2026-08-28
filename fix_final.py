
import re
with open("internal/server/server.go", "a", encoding="utf-8") as f:
    f.write("""

func withLog(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s %v", r.Method, r.URL.Path, time.Since(start))
	})
}

func (s *Server) login(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Password string `json:"password"`
	}
	json.NewDecoder(r.Body).Decode(&body)
	if s.st.VerifyPassword(body.Password) {
		w.Header().Set("Set-Cookie", "token=admin; Path=/; HttpOnly")
		w.Write([]byte(`{"status":"ok"}`))
	} else {
		w.WriteHeader(401)
		w.Write([]byte(`{"error":"wrong password"}`))
	}
}
""")

