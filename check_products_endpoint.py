
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()
    idx = text.find("func (s *Server) products")
    print(text[idx:idx+500])

