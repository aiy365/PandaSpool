
import re
with open("internal/store/store.go", "r", encoding="utf-8") as f:
    text = f.read()

old_ezviz = """	Ezviz struct {
		AppKey       string `json:"app_key"`
		AppSecret    string `json:"app_secret"`
		DeviceSerial string `json:"device_serial"`
		Channel      string `json:"channel"`
		VerifyCode   string `json:"verify_code"`
		Rotation     string `json:"rotation"`
	} `json:"ezviz"`"""

new_ezviz = """	Ezviz struct {
		AppKey       string `json:"app_key"`
		AppSecret    string `json:"app_secret"`
		DeviceSerial string `json:"device_serial"`
		Channel      string `json:"channel"`
		VerifyCode   string `json:"verify_code"`
		Rotation     string `json:"rotation"`
		Crop         string `json:"crop"`
	} `json:"ezviz"`"""

text = text.replace(old_ezviz, new_ezviz)

with open("internal/store/store.go", "w", encoding="utf-8") as f:
    f.write(text)

