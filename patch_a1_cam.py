# -*- coding: utf-8 -*-
# 中枢加 A1 内置摄像头：chamber-image 协议客户端 + /api/camera/a1.jpeg 路由
import io

p = r"C:\work\3D模型\printpilot-hub\internal\server\server.go"
s = io.open(p, encoding="utf-8").read()

# 1) imports: crypto/tls 与 net
old = '''import (
	"crypto/aes"
	"crypto/cipher"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"io/fs"
	"log"
	"net/http"'''
new = '''import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/tls"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"io/fs"
	"log"
	"net"
	"net/http"'''
assert s.count(old) == 1
s = s.replace(old, new)

# 2) 路由注册
old = '''	mux.HandleFunc("/api/camera", s.auth(s.camera))'''
new = '''	mux.HandleFunc("/api/camera", s.auth(s.camera))
	mux.HandleFunc("/api/camera/a1.jpeg", s.auth(s.cameraA1))'''
assert s.count(old) == 1
s = s.replace(old, new)

# 3) 客户端实现 + handler（放在 camera handler 前）
old = '''func (s *Server) camera(w http.ResponseWriter, r *http.Request) {'''
new = '''// a1CameraJPEG 从 A1 内置摄像头取一帧（LAN 直连 chamber-image 协议：
// 6000 端口 TLS + 80 字节鉴权块 + 16 字节帧头 + JPEG）。
func a1CameraJPEG(ip, accessCode string) ([]byte, error) {
	raw, err := net.DialTimeout("tcp", net.JoinHostPort(ip, "6000"), 5*time.Second)
	if err != nil {
		return nil, err
	}
	conn := tls.Client(raw, &tls.Config{InsecureSkipVerify: true, MinVersion: tls.VersionTLS12})
	defer conn.Close()
	conn.SetDeadline(time.Now().Add(10 * time.Second))

	payload := make([]byte, 80)
	binary.LittleEndian.PutUint32(payload[0:4], 0x40)   // magic
	binary.LittleEndian.PutUint32(payload[4:8], 0x3000) // command
	copy(payload[16:48], "bblp")
	copy(payload[48:80], accessCode)
	if _, err := conn.Write(payload); err != nil {
		return nil, err
	}

	header := make([]byte, 16)
	if _, err := io.ReadFull(conn, header); err != nil {
		return nil, err
	}
	size := binary.LittleEndian.Uint32(header[0:4])
	if size == 0 || size > 10<<20 {
		return nil, fmt.Errorf("camera: invalid frame size %d", size)
	}
	jpeg := make([]byte, size)
	if _, err := io.ReadFull(conn, jpeg); err != nil {
		return nil, err
	}
	if len(jpeg) < 3 || jpeg[0] != 0xFF || jpeg[1] != 0xD8 {
		return nil, fmt.Errorf("camera: not a JPEG frame")
	}
	return jpeg, nil
}

// cameraA1 输出 A1 内置摄像头快照（需会话鉴权；仅局域网直连可达时有效）。
func (s *Server) cameraA1(w http.ResponseWriter, r *http.Request) {
	cfg := s.st.LoadSettings()
	ip, code := strings.TrimSpace(cfg.Bambu.LanHost), cfg.Bambu.LanCode
	if ip == "" || code == "" {
		http.Error(w, "camera: LAN direct-connect not configured", http.StatusServiceUnavailable)
		return
	}
	jpeg, err := a1CameraJPEG(ip, code)
	if err != nil {
		http.Error(w, "camera: "+err.Error(), http.StatusBadGateway)
		return
	}
	w.Header().Set("Content-Type", "image/jpeg")
	w.Header().Set("Cache-Control", "no-store")
	w.Write(jpeg)
}

func (s *Server) camera(w http.ResponseWriter, r *http.Request) {'''
assert s.count(old) == 1
s = s.replace(old, new)

io.open(p, "w", encoding="utf-8", newline="").write(s)
print("server.go camera added")
