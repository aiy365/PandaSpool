
import re
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

text = re.sub(r"func \(s \*Server\) static\(\) http\.HandlerFunc \{.*?\n\}", """func (s *Server) static() http.Handler {
	fSys, _ := fs.Sub(web.FS, "dist")
	return http.FileServer(http.FS(fSys))
}""", text, flags=re.DOTALL)

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

