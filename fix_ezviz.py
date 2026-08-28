
import re

with open("internal/server/notify.go", "r", encoding="utf-8") as f:
    text = f.read()

# Fix unused imports
text = text.replace("\"net/url\"\n", "")
text = text.replace("\"strings\"\n", "")

ezviz_code = """
	var picUrl string
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
	}
"""
text = re.sub(r"cfg := s\.st\.LoadSettings\(\)\n.*?if cfg\.Ezviz\.AppKey.*?\}\n\t\}\n\t\}", ezviz_code.strip(), text, flags=re.DOTALL)
text = text.replace("\"net/http\"", "\"net/http\"\n\t\"net/url\"")

with open("internal/server/notify.go", "w", encoding="utf-8") as f:
    f.write(text)

