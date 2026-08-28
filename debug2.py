
import re

with open("internal/server/notify.go", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("""func (s *Server) sendWebhookNotification(title string, st map[string]any) {""", """func (s *Server) sendWebhookNotification(title string, st map[string]any) {
	fmt.Println("sendWebhookNotification CALLED with title:", title)""")

text = text.replace("""if wcCorp != "" && wcSec != "" {""", """fmt.Println("WeCom Config:", wcCorp, len(wcSec))
	if wcCorp != "" && wcSec != "" {""")

with open("internal/server/notify.go", "w", encoding="utf-8") as f:
    f.write(text)

