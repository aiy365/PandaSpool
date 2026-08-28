
missing = """
func (s *Server) ewelinkToken(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) ewDevices(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) ewSwitch(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) products(w http.ResponseWriter, r *http.Request) {
	if r.Method == "GET" {
		res, _ := s.st.ListProducts()
		json.NewEncoder(w).Encode(res)
	} else {
		var req store.Product
		json.NewDecoder(r.Body).Decode(&req)
		res, _ := s.st.SaveProduct(req)
		json.NewEncoder(w).Encode(res)
	}
}
func (s *Server) productItem(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(r.URL.Path, "/")
	id := parts[len(parts)-1]
	if r.Method == "DELETE" {
		s.st.DeleteProduct(id)
	} else {
		res, _ := s.st.GetProduct(id)
		json.NewEncoder(w).Encode(res)
	}
}
func (s *Server) authAI(next http.HandlerFunc) http.HandlerFunc { return next }
func (s *Server) inboxItem(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) presetItem(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) colors(w http.ResponseWriter, r *http.Request) {
	if r.Method == "GET" {
		q := r.URL.Query().Get("product_id")
		res, _ := s.st.ListColors(q)
		json.NewEncoder(w).Encode(res)
	} else {
		var req store.Color
		json.NewDecoder(r.Body).Decode(&req)
		res, _ := s.st.SaveColor(req)
		json.NewEncoder(w).Encode(res)
	}
}
func (s *Server) stockIns(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) claims(w http.ResponseWriter, r *http.Request) {
	if r.Method == "GET" {
		q := r.URL.Query().Get("product_id")
		res, _ := s.st.ListClaims(q)
		json.NewEncoder(w).Encode(res)
	} else {
		var req store.Claim
		json.NewDecoder(r.Body).Decode(&req)
		res, _ := s.st.SaveClaim(req)
		json.NewEncoder(w).Encode(res)
	}
}
func (s *Server) reviewClaim(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) compare(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) drafts(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) claimConflicts(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) pack(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) proxy(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) upload(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) deleteUpload(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) aiMaterials(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) aiDrafts(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) llmsTxt(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) authDesk(next http.HandlerFunc) http.HandlerFunc { return next }
func (s *Server) desk(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) machine(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) actuator(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) camera(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) air(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) ingestAir(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) static() http.HandlerFunc { return func(w http.ResponseWriter, r *http.Request) { http.ServeFile(w, r, "web/dist" + r.URL.Path) } }
"""
with open("internal/server/server.go", "a", encoding="utf-8") as f:
    f.write("\n" + missing)

