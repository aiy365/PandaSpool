package store

import "testing"

func TestBuildCardSpecsMergesDryingAndPrefersRange(t *testing.T) {
	got := BuildCardSpecs([]Claim{
		{Key: "烘干温度", Value: "50", Unit: "°C", Status: ClaimConfirmed, CreatedAt: "1", Source: "资料"},
		{Key: "烘干温度范围", Value: "60-65", Unit: "°C", Status: ClaimConfirmed, CreatedAt: "2", Source: "资料"},
		{Key: "烘干时间", Value: "4-8", Unit: "h", Status: ClaimConfirmed, CreatedAt: "2", Source: "资料"},
		{Key: "喷嘴温度范围", Value: "230-260", Unit: "°C", Status: ClaimConfirmed, Source: "资料"},
		{Key: "热床温度范围", Value: "70-90", Unit: "°C", Status: ClaimConfirmed, Source: "资料"},
		{Key: "打印速度上限", Value: "<300", Unit: "mm/s", Status: ClaimConfirmed, Source: "资料"},
		{Key: "打印速度", Value: "50-200", Unit: "mm/s", Status: ClaimConfirmed, CreatedAt: "1", Source: "资料"},
	})
	if got["烘干"] != "60-65°C, 4-8小时" {
		t.Fatalf("烘干 %q", got["烘干"])
	}
	if got["喷嘴"] != "230-260°C" {
		t.Fatalf("喷嘴 %q", got["喷嘴"])
	}
	if got["热床"] != "70-90°C" {
		t.Fatalf("热床 %q", got["热床"])
	}
	if got["速度"] != "<300mm/s" {
		t.Fatalf("速度 %q", got["速度"])
	}
}

func TestBuildCardSpecsHoursFromRaw(t *testing.T) {
	got := BuildCardSpecs([]Claim{
		{Key: "烘干温度", Value: "65-70", Unit: "°C", Raw: "8-12小时", Status: ClaimConfirmed, Source: "资料"},
	})
	if got["烘干"] != "65-70°C, 8-12小时" {
		t.Fatalf("烘干 %q", got["烘干"])
	}
}

func TestBuildCardSpecsSkipsStudioDraftAndColor(t *testing.T) {
	got := BuildCardSpecs([]Claim{
		{Key: "喷嘴推荐温度", Value: "220", Unit: "°C", Status: ClaimConfirmed, Source: "Studio"},
		{Key: "喷嘴温度范围", Value: "190-230", Unit: "°C", Status: ClaimDraft, Source: "资料"},
		{Key: "热床温度范围", Value: "50-60", Unit: "°C", Status: ClaimConfirmed, Source: "资料", ColorID: "c1"},
		{Key: "烘干", Value: "55°C, 8小时", Status: ClaimConfirmed, Source: "资料"},
	})
	if got["烘干"] != "55°C, 8小时" {
		t.Fatalf("烘干 %q", got["烘干"])
	}
	if _, ok := got["喷嘴"]; ok {
		t.Fatalf("studio/draft leaked: %v", got)
	}
	if _, ok := got["热床"]; ok {
		t.Fatalf("color-scoped leaked: %v", got)
	}
}
