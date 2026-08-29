package ezviz

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

// ErrTokenInvalid 表示平台明确回复 token 不可用（10002/10001）。
// 萤石每次发新 token 会作废旧 token（换 AppSecret、他处重新获取都会触发），
// 调用方拿到这个错应当强制刷新一次再试。
var ErrTokenInvalid = errors.New("ezviz token 过期或被作废")

type Client struct {
	mu     sync.Mutex
	appKey string
	secret string
	token  string
	expire time.Time
	err    string
	// token 换新后回调（server 层落库，重启后接着用，避免每次重启都换 token）。
	onRefresh func(at string, expireAt time.Time)
}

func New() *Client { return &Client{} }

func (c *Client) Configure(appKey, secret string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.appKey, c.secret = strings.TrimSpace(appKey), strings.TrimSpace(secret)
}

func (c *Client) OnTokenRefresh(f func(at string, expireAt time.Time)) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.onRefresh = f
}

// SetSeed 用持久化的 token 预热缓存；过期则忽略。
func (c *Client) SetSeed(at string, expireAt time.Time) {
	at = strings.TrimSpace(at)
	if at == "" || !expireAt.After(time.Now()) {
		return
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	c.token = at
	c.expire = expireAt
}

func (c *Client) Status() map[string]any {
	c.mu.Lock()
	defer c.mu.Unlock()
	return map[string]any{
		"configured": c.appKey != "" && c.secret != "",
		"has_token":  c.token != "" && time.Now().Before(c.expire),
		"error":      c.err,
	}
}

func (c *Client) AccessToken() (string, error) {
	c.mu.Lock()
	if c.token != "" && time.Now().Before(c.expire.Add(-2*time.Minute)) {
		t := c.token
		c.mu.Unlock()
		return t, nil
	}
	key, secret := c.appKey, c.secret
	c.mu.Unlock()
	return c.fetchToken(key, secret)
}

// RefreshNow 强制换新 token（旧 token 在平台上被作废时用）。
func (c *Client) RefreshNow() (string, error) {
	c.mu.Lock()
	key, secret := c.appKey, c.secret
	c.token = ""
	c.mu.Unlock()
	if key == "" || secret == "" {
		return "", fmt.Errorf("未填写萤石 AppKey/AppSecret")
	}
	return c.fetchToken(key, secret)
}

func (c *Client) fetchToken(key, secret string) (string, error) {
	if key == "" || secret == "" {
		return "", fmt.Errorf("未填写萤石 AppKey/AppSecret")
	}
	form := url.Values{}
	form.Set("appKey", key)
	form.Set("appSecret", secret)
	res, err := http.PostForm("https://open.ys7.com/api/lapp/token/get", form)
	if err != nil {
		return "", err
	}
	defer res.Body.Close()
	raw, _ := io.ReadAll(res.Body)
	var parsed struct {
		Code string `json:"code"`
		Msg  string `json:"msg"`
		Data struct {
			AccessToken string `json:"accessToken"`
			ExpireTime  int64  `json:"expireTime"`
		} `json:"data"`
	}
	_ = json.Unmarshal(raw, &parsed)
	if parsed.Code != "200" || parsed.Data.AccessToken == "" {
		return "", fmt.Errorf("萤石 token 失败: %s %s", parsed.Code, parsed.Msg)
	}
	expire := time.Now().Add(6 * time.Hour)
	if parsed.Data.ExpireTime > 0 {
		expire = time.UnixMilli(parsed.Data.ExpireTime)
	}
	c.mu.Lock()
	c.token = parsed.Data.AccessToken
	c.expire = expire
	c.err = ""
	f := c.onRefresh
	c.mu.Unlock()
	if f != nil {
		f(parsed.Data.AccessToken, expire)
	}
	return parsed.Data.AccessToken, nil
}

type DeviceInfo struct {
	Online    int  `json:"status"`    // 1 在线
	IsEncrypt int  `json:"isEncrypt"` // 1 = 开启视频加密
	Model     string `json:"model"`
	Name      string `json:"deviceName"`
}

// DeviceInfo 查设备状态；token 失效返回 ErrTokenInvalid。
func (c *Client) DeviceInfo(accessToken, deviceSerial string) (*DeviceInfo, error) {
	form := url.Values{}
	form.Set("accessToken", accessToken)
	form.Set("deviceSerial", deviceSerial)
	res, err := http.PostForm("https://open.ys7.com/api/lapp/device/info", form)
	if err != nil {
		return nil, err
	}
	defer res.Body.Close()
	raw, _ := io.ReadAll(res.Body)
	var parsed struct {
		Code string `json:"code"`
		Msg  string `json:"msg"`
		Data *DeviceInfo `json:"data"`
	}
	_ = json.Unmarshal(raw, &parsed)
	if parsed.Code == "10002" || parsed.Code == "10001" {
		return nil, ErrTokenInvalid
	}
	if parsed.Code != "200" || parsed.Data == nil {
		return nil, fmt.Errorf("萤石设备查询失败: %s %s", parsed.Code, parsed.Msg)
	}
	return parsed.Data, nil
}

// EnsureToken 返回一个可用的 token：先取缓存，平台报 token 失效时自动换新一次。
// 设备查询本身失败（网络等）不触发刷新，直接返回缓存 token 由上层兜底。
func (c *Client) EnsureToken(deviceSerial string) (string, *DeviceInfo, error) {
	token, err := c.AccessToken()
	if err != nil {
		return "", nil, err
	}
	if deviceSerial == "" {
		return token, nil, nil
	}
	info, derr := c.DeviceInfo(token, deviceSerial)
	if errors.Is(derr, ErrTokenInvalid) {
		token, err = c.RefreshNow()
		if err != nil {
			return "", nil, err
		}
		info, derr = c.DeviceInfo(token, deviceSerial)
	}
	if derr != nil {
		// 设备离线/序列号不对等业务错误：token 本身仍是最新，交上层提示。
		return token, nil, derr
	}
	return token, info, nil
}
