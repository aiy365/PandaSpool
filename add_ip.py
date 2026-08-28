
import re

with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("mux.HandleFunc(\"/api/notify/test\", s.testNotify)", """mux.HandleFunc("/api/notify/test", s.testNotify)
	mux.HandleFunc("/api/server-ip", func(w http.ResponseWriter, r *http.Request) {
		res, err := http.Get("https://api.ipify.org")
		if err == nil {
			defer res.Body.Close()
			io.Copy(w, res.Body)
		}
	})""")

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

