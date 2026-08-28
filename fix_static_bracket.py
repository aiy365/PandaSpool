
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("} }\\n\\nfunc (s *Server) applyIntegrations() {", "}\\n\\nfunc (s *Server) applyIntegrations() {")

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

