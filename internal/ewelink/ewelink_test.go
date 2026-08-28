package ewelink

import (
	"strings"
	"testing"
)

func TestNormalizePhone(t *testing.T) {
	cases := map[string]string{
		"13800138000":    "+8613800138000",
		"+8613800138000": "+8613800138000",
		"8613800138000":  "+8613800138000",
		"138 0013 8000":  "+8613800138000",
	}
	for in, want := range cases {
		if got := normalizePhone(in); got != want {
			t.Fatalf("normalizePhone(%q)=%q want %q", in, got, want)
		}
	}
}

func TestParseRef(t *testing.T) {
	id, out, err := parseRef("1000abc")
	if err != nil || id != "1000abc" || out != nil {
		t.Fatalf("single: %s %v %v", id, out, err)
	}
	id, out, err = parseRef("1000abc:2")
	if err != nil || id != "1000abc" || out == nil || *out != 2 {
		t.Fatalf("outlet: %s %v %v", id, out, err)
	}
	if _, _, err = parseRef(""); err == nil {
		t.Fatal("empty should fail")
	}
	if _, _, err = parseRef("1000abc:x"); err == nil {
		t.Fatal("bad outlet should fail")
	}
}

func TestExpandTriple(t *testing.T) {
	item := map[string]any{
		"deviceid":     "1000aaa",
		"name":         "三联",
		"online":       true,
		"productModel": "SWITCH-3",
		"extra":        map[string]any{"uiid": 8.0},
		"params": map[string]any{
			"switches": []any{
				map[string]any{"outlet": 0.0, "switch": "on"},
				map[string]any{"outlet": 1.0, "switch": "off"},
				map[string]any{"outlet": 2.0, "switch": "on"},
			},
		},
		"tags": map[string]any{
			"ck_channel_name": map[string]any{"0": "仓内长开", "1": "打印加强", "2": "车间"},
		},
	}
	got := expandDevice(item)
	if len(got) != 3 {
		t.Fatalf("want 3 channels, got %d", len(got))
	}
	if got[0].ID != "1000aaa:0" || got[0].Name != "三联 · 通道1 仓内长开" {
		t.Fatalf("ch0 %+v", got[0])
	}
	if got[1].On == nil || *got[1].On {
		t.Fatalf("ch1 should be off")
	}
}

func TestLoginErrHint(t *testing.T) {
	s := loginErr(407, "", "")
	if !strings.Contains(s, "APPID") {
		t.Fatalf("hint: %s", s)
	}
}

func TestHostForChina(t *testing.T) {
	for _, in := range []string{"", "cn", "CN", "中国", "china"} {
		if got := hostFor(in); got != "https://cn-apia.coolkit.cn" {
			t.Fatalf("hostFor(%q)=%s", in, got)
		}
	}
}

func TestMD5Hex(t *testing.T) {
	if md5Hex("abc") != "900150983cd24fb0d6963f7d28e17f72" {
		t.Fatal(md5Hex("abc"))
	}
}
