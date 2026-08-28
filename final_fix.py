
import re

with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

# Add log import if not present
if "\"log\"" not in text:
    text = text.replace("\"fmt\"", "\"fmt\"\n\t\"log\"")

# Fix camera using s.cfg
text = text.replace("s.cfg.", "cfg.")
text = text.replace("func (s *Server) camera(w http.ResponseWriter, r *http.Request) {\n\tvar picUrl string", "func (s *Server) camera(w http.ResponseWriter, r *http.Request) {\n\tcfg := s.st.LoadSettings()\n\tvar picUrl string")

# Fix static
text = re.sub(
    r"func \(s \*Server\) static\(\) http\.HandlerFunc \{.*?\}",
    """func (s *Server) static() http.HandlerFunc {
\tdir, _ := fs.Sub(web.Static, "dist")
\treturn http.FileServer(http.FS(dir)).ServeHTTP
}""",
    text
)

# Remove the first applyIntegrations
text = re.sub(r"func \(s \*Server\) applyIntegrations\(\) \{\n\tcfg := s\.st\.LoadSettings\(\)\n\ts\.ez\.Configure\(cfg\.Ezviz\.AppKey, cfg\.Ezviz\.AppSecret\)\n\}", "", text)

# Fix login
text = text.replace("s.st.VerifyPassword(body.Password)", "s.st.CheckAdmin(\"admin\", body.Password)")

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

