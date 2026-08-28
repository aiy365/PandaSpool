
import re
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

# restore verifyWeCom
verify_code = """
func (s *Server) verifyWeCom(w http.ResponseWriter, r *http.Request) {
	echostr := r.URL.Query().Get("echostr")
	cfg := s.st.LoadSettings()
	aesKeyStr := cfg.Automations.WeComAESKey
	if aesKeyStr == "" || echostr == "" {
		w.Write([]byte("error"))
		return
	}

	aesKey, err := base64.StdEncoding.DecodeString(aesKeyStr + "=")
	if err != nil {
		w.Write([]byte("error"))
		return
	}
	
	ciphertext, err := base64.StdEncoding.DecodeString(echostr)
	if err != nil {
		ciphertext, err = base64.StdEncoding.DecodeString(strings.ReplaceAll(echostr, " ", "+"))
		if err != nil {
			w.Write([]byte("error"))
			return
		}
	}
	
	block, err := aes.NewCipher(aesKey)
	if err != nil {
		w.Write([]byte("error"))
		return
	}
	mode := cipher.NewCBCDecrypter(block, aesKey[:16])
	
	plaintext := make([]byte, len(ciphertext))
	mode.CryptBlocks(plaintext, ciphertext)
	
	pad := int(plaintext[len(plaintext)-1])
	if len(plaintext) < pad {
		w.Write([]byte("error"))
		return
	}
	plaintext = plaintext[:len(plaintext)-pad]
	
	if len(plaintext) < 20 {
		w.Write([]byte("error"))
		return
	}
	content := plaintext[16:]
	
	msgLen := binary.BigEndian.Uint32(content[:4])
	if len(content) < int(4+msgLen) {
		w.Write([]byte("error"))
		return
	}
	
	msg := content[4 : 4+msgLen]
	w.Write(msg)
}
"""

if "func (s *Server) verifyWeCom" not in text:
    text += verify_code

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

