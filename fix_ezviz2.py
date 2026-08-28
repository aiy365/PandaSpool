
import re

with open("internal/server/notify.go", "r", encoding="utf-8") as f:
    text = f.read()

old_ezviz = """	var picUrl string
	cfg := s.st.LoadSettings()
	if cfg.Ezviz.AppKey != "" && cfg.Ezviz.DeviceSerial != "" {
		if token, _ := s.ez.GetToken(cfg.Ezviz.AppKey, cfg.Ezviz.AppSecret); token != "" {
			if pic, _ := s.ez.Capture(token, cfg.Ezviz.DeviceSerial, cfg.Ezviz.Channel); pic != "" {
				picUrl = pic
			}
		}
	}"""

new_ezviz = """	var picUrl string
	cfg := s.st.LoadSettings()
	if cfg.Ezviz.AppKey != "" && cfg.Ezviz.DeviceSerial != "" {
		s.ez.Configure(cfg.Ezviz.AppKey, cfg.Ezviz.AppSecret)
		if token, err := s.ez.AccessToken(); err == nil && token != "" {
			form := url.Values{}
			form.Set("accessToken", token)
			form.Set("deviceSerial", cfg.Ezviz.DeviceSerial)
			channel := cfg.Ezviz.Channel
			if channel == "" {
				channel = "1"
			}
			form.Set("channelNo", channel)
			if res, err := http.PostForm("https://open.ys7.com/api/lapp/device/capture", form); err == nil {
				defer res.Body.Close()
				raw, _ := io.ReadAll(res.Body)
				var parsed struct {
					Data struct {
						PicUrl string `json:"picUrl"`
					} `json:"data"`
				}
				if json.Unmarshal(raw, &parsed) == nil && parsed.Data.PicUrl != "" {
					picUrl = parsed.Data.PicUrl
				}
			}
		}
	}"""

text = text.replace(old_ezviz, new_ezviz)

with open("internal/server/notify.go", "w", encoding="utf-8") as f:
    f.write(text)

import os
os.system("goimports -w internal/server/notify.go internal/server/server.go")

