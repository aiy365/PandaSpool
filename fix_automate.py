
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

old_automate = """func (s *Server) automate() {
	for {
		time.Sleep(10 * time.Second)
		cfg := s.st.LoadSettings()"""
new_automate = """func (s *Server) automate() {
	for {
		time.Sleep(10 * time.Second)
		s.tickNotifications()
		cfg := s.st.LoadSettings()"""
text = text.replace(old_automate, new_automate)

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

