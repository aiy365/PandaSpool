
import re

with open("internal/server/notify.go", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("http.DefaultClient.Do(req)", """resp, err := http.DefaultClient.Do(req)
				if err != nil {
					fmt.Println("WeCom Send Error:", err)
				} else {
					defer resp.Body.Close()
					rb, _ := io.ReadAll(resp.Body)
					fmt.Println("WeCom Send Response:", string(rb))
				}""")

with open("internal/server/notify.go", "w", encoding="utf-8") as f:
    f.write(text)

