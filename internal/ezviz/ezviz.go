package ezviz

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

type Client struct {
	mu     sync.Mutex
	appKey string
	secret string
	token  string
	expire time.Time
	err    string
}

func New() *Client { return &Client{} }

func (c *Client) Configure(appKey, secret string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.appKey, c.secret = strings.TrimSpace(appKey), strings.TrimSpace(secret)
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
	c.mu.Lock()
	c.token = parsed.Data.AccessToken
	if parsed.Data.ExpireTime > 0 {
		c.expire = time.UnixMilli(parsed.Data.ExpireTime)
	} else {
		c.expire = time.Now().Add(6 * time.Hour)
	}
	c.err = ""
	c.mu.Unlock()
	return parsed.Data.AccessToken, nil
}
