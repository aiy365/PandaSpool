
import re

with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

# Replace the camera handler
new_camera = """func (s *Server) camera(w http.ResponseWriter, r *http.Request) {
\tcfg := s.st.LoadSettings()
\ttoken, err := s.ez.AccessToken()
\tif err != nil {
\t\thttp.Error(w, err.Error(), 500)
\t\treturn
\t}
\tchannel := cfg.Ezviz.Channel
\tif channel == "" { channel = "1" }
\turlStr := fmt.Sprintf("ezopen://open.ys7.com/%s/%s.hd.live", cfg.Ezviz.DeviceSerial, channel)
\tif cfg.Ezviz.VerifyCode != "" {
\t\turlStr = fmt.Sprintf("ezopen://%s@open.ys7.com/%s/%s.hd.live", cfg.Ezviz.VerifyCode, cfg.Ezviz.DeviceSerial, channel)
\t}
\tjson.NewEncoder(w).Encode(map[string]string{
\t\t"accessToken": token,
\t\t"url": urlStr,
\t})
}"""

text = re.sub(r"func \(s \*Server\) camera\(w http\.ResponseWriter, r \*http\.Request\) \{.*?\n\}", new_camera, text, flags=re.DOTALL)

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

