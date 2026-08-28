
import re

with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

# I will replace the mocked functions at the bottom.
mock_block = """
func (s *Server) presetItem(w http.ResponseWriter, r *http.Request) { w.Write([]byte("{\\"status\\":\\"ok\\"}")) }
func (s *Server) colors(w http.ResponseWriter, r *http.Request) { w.Write([]byte("{\\"status\\":\\"ok\\"}")) }
func (s *Server) stockIns(w http.ResponseWriter, r *http.Request) { w.Write([]byte("{\\"status\\":\\"ok\\"}")) }
func (s *Server) claims(w http.ResponseWriter, r *http.Request) { w.Write([]byte("{\\"status\\":\\"ok\\"}")) }
func (s *Server) reviewClaim(w http.ResponseWriter, r *http.Request) { w.Write([]byte("{\\"status\\":\\"ok\\"}")) }
func (s *Server) compare(w http.ResponseWriter, r *http.Request) { w.Write([]byte("{\\"status\\":\\"ok\\"}")) }
func (s *Server) drafts(w http.ResponseWriter, r *http.Request)  { w.Write([]byte("{\\"status\\":\\"ok\\"}")) }
func (s *Server) claimConflicts(w http.ResponseWriter, r *http.Request) { w.Write([]byte("{\\"status\\":\\"ok\\"}")) }
func (s *Server) pack(w http.ResponseWriter, r *http.Request)   { w.Write([]byte("{\\"status\\":\\"ok\\"}")) }
func (s *Server) proxy(w http.ResponseWriter, r *http.Request)  { w.Write([]byte("{\\"status\\":\\"ok\\"}")) }
func (s *Server) upload(w http.ResponseWriter, r *http.Request) { w.Write([]byte("{\\"status\\":\\"ok\\"}")) }
func (s *Server) deleteUpload(w http.ResponseWriter, r *http.Request) { w.Write([]byte("{\\"status\\":\\"ok\\"}")) }
func (s *Server) aiMaterials(w http.ResponseWriter, r *http.Request) { w.Write([]byte("{\\"status\\":\\"ok\\"}")) }
func (s *Server) aiDrafts(w http.ResponseWriter, r *http.Request) { w.Write([]byte("{\\"status\\":\\"ok\\"}")) }
func (s *Server) llmsTxt(w http.ResponseWriter, r *http.Request)  { w.Write([]byte("{\\"status\\":\\"ok\\"}")) }
func (s *Server) authDesk(next http.HandlerFunc) http.HandlerFunc { return next }
"""

restored_methods = """
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
func (s *Server) compare(w http.ResponseWriter, r *http.Request) { 
	res, _ := s.st.Compare()
	json.NewEncoder(w).Encode(res)
}
func (s *Server) drafts(w http.ResponseWriter, r *http.Request)  { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) claimConflicts(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) pack(w http.ResponseWriter, r *http.Request)   { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) proxy(w http.ResponseWriter, r *http.Request)  { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) upload(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) deleteUpload(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) aiMaterials(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) aiDrafts(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) llmsTxt(w http.ResponseWriter, r *http.Request)  { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) authDesk(next http.HandlerFunc) http.HandlerFunc { return next }
"""

# Wait, compare method! Does store have Compare()?
"""

text = text.replace(mock_block.strip(), restored_methods.strip())

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

