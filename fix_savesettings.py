
import re

with open("internal/store/store.go", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("""	if in.Air.Token == "" {""", """	if in.Automations.WeComSecret == "" {
		in.Automations.WeComSecret = cur.Automations.WeComSecret
	}
	if in.Automations.WeComAESKey == "" {
		in.Automations.WeComAESKey = cur.Automations.WeComAESKey
	}
	if in.Air.Token == "" {""")

text = text.replace("""	if in.Ezviz.VerifyCode != "" {
		in.Ezviz.VerifyCode = "********"
	}""", """	if in.Ezviz.VerifyCode != "" {
		in.Ezviz.VerifyCode = "********"
	}
	if in.Automations.WeComSecret != "" {
		in.Automations.WeComSecret = "********"
	}
	if in.Automations.WeComAESKey != "" {
		in.Automations.WeComAESKey = "********"
	}""")

with open("internal/store/store.go", "w", encoding="utf-8") as f:
    f.write(text)

