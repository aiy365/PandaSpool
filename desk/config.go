package main

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
)

type Config struct {
	mu     sync.RWMutex
	URL    string
	Token  string
	Poll   int
	Show   map[string]bool
	path   string
}

var showKeys = []struct{ Key, Label string }{
	{"eta", "完成时间"},
	{"progress", "进度"},
	{"state", "状态"},
	{"nozzle", "喷嘴"},
	{"bed", "热床"},
	{"layer", "层数"},
	{"remaining", "剩余"},
	{"job", "任务名"},
	{"pm25", "PM2.5"},
	{"presence", "有人"},
	{"connected", "连接"},
}

func defaultShow() map[string]bool {
	m := map[string]bool{}
	for _, k := range showKeys {
		m[k.Key] = true
	}
	return m
}

func iniPath() string {
	exe, err := os.Executable()
	if err != nil {
		return "pandaspool-desk.ini"
	}
	return filepath.Join(filepath.Dir(exe), "pandaspool-desk.ini")
}

func loadConfig() *Config {
	c := &Config{
		URL:  "https://3d.bstccc.cn",
		Poll: 30,
		Show: defaultShow(),
		path: iniPath(),
	}
	f, err := os.Open(c.path)
	if err != nil {
		return c
	}
	defer f.Close()
	section := ""
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") || strings.HasPrefix(line, ";") {
			continue
		}
		if strings.HasPrefix(line, "[") && strings.HasSuffix(line, "]") {
			section = strings.ToLower(strings.Trim(line, "[]"))
			continue
		}
		k, v, ok := strings.Cut(line, "=")
		if !ok {
			continue
		}
		k = strings.TrimSpace(k)
		v = strings.TrimSpace(v)
		switch section {
		case "server":
			switch k {
			case "url":
				c.URL = strings.TrimRight(v, "/")
			case "token":
				c.Token = v
			}
		case "poll":
			if k == "seconds" {
				if n, err := strconv.Atoi(v); err == nil && n >= 2 {
					c.Poll = n
				}
			}
		case "show":
			c.Show[k] = v == "1" || strings.EqualFold(v, "true") || v == "yes"
		}
	}
	return c
}

func (c *Config) snapshot() (url, token string, poll int, show map[string]bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	show = map[string]bool{}
	for k, v := range c.Show {
		show[k] = v
	}
	return c.URL, c.Token, c.Poll, show
}

func (c *Config) showing(key string) bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	v, ok := c.Show[key]
	return !ok || v
}

func (c *Config) save() error {
	c.mu.RLock()
	defer c.mu.RUnlock()
	var b strings.Builder
	b.WriteString("[server]\n")
	fmt.Fprintf(&b, "url=%s\n", c.URL)
	fmt.Fprintf(&b, "token=%s\n\n", c.Token)
	b.WriteString("[poll]\n")
	fmt.Fprintf(&b, "seconds=%d\n\n", c.Poll)
	b.WriteString("[show]\n")
	for _, k := range showKeys {
		v := "1"
		if !c.Show[k.Key] {
			v = "0"
		}
		fmt.Fprintf(&b, "%s=%s\n", k.Key, v)
	}
	return os.WriteFile(c.path, []byte(b.String()), 0600)
}
