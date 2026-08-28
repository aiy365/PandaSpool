package store

import (
	"regexp"
	"strings"
)

func (p *Product) attachCard(claims []Claim) {
	p.Card = BuildCardSpecs(claims)
}

var dryingHoursRe = regexp.MustCompile(`(?i)(\d+(?:\s*[-~–—]\s*\d+)?)\s*(小时|h\b|hrs?\b|hours?\b)`)

func looksLikeHours(s string) bool {
	return dryingHoursRe.FindStringIndex(s) != nil
}

func compactRange(s string) string {
	s = strings.TrimSpace(s)
	s = strings.ReplaceAll(s, " ", "")
	s = strings.ReplaceAll(s, "–", "-")
	s = strings.ReplaceAll(s, "—", "-")
	s = strings.ReplaceAll(s, "~", "-")
	return s
}

func dryingHoursFromRaw(raw string) Claim {
	m := dryingHoursRe.FindStringSubmatch(raw)
	if m == nil {
		return Claim{}
	}
	return Claim{Value: compactRange(m[1]), Unit: "小时"}
}

func prettyUnit(unit string) string {
	switch strings.ToLower(strings.TrimSpace(unit)) {
	case "h", "hr", "hrs", "hour", "hours":
		return "小时"
	default:
		return strings.TrimSpace(unit)
	}
}

func fmtClaim(c Claim) string {
	v := strings.TrimSpace(c.Value)
	u := prettyUnit(c.Unit)
	if u == "" {
		return v
	}
	if strings.Contains(v, u) {
		return v
	}
	low := strings.ToLower(v)
	if u == "小时" && (strings.HasSuffix(low, "h") || strings.Contains(v, "小时")) {
		return v
	}
	return strings.TrimSpace(v + u)
}

func latestByKeys(best map[string]Claim, keys ...string) (Claim, bool) {
	for _, k := range keys {
		if c, ok := best[k]; ok && strings.TrimSpace(c.Value) != "" {
			return c, true
		}
	}
	return Claim{}, false
}

func dryingSpec(best map[string]Claim) string {
	t, tok := latestByKeys(best, "烘干温度范围", "烘干温度")
	h, hok := latestByKeys(best, "烘干时间")
	if !hok && tok {
		if extra := dryingHoursFromRaw(t.Raw); extra.Value != "" {
			h, hok = extra, true
		}
	}
	combined, cok := latestByKeys(best, "烘干")
	switch {
	case tok && hok:
		return fmtClaim(t) + ", " + fmtClaim(h)
	case cok:
		s := fmtClaim(combined)
		if hok && !looksLikeHours(s) {
			return s + ", " + fmtClaim(h)
		}
		return s
	case tok:
		return fmtClaim(t)
	default:
		return ""
	}
}

func BuildCardSpecs(claims []Claim) map[string]string {
	best := map[string]Claim{}
	for _, c := range claims {
		if c.Status != "" && c.Status != ClaimConfirmed {
			continue
		}
		if c.ColorID != "" {
			continue
		}
		if c.Source == "Studio" {
			continue
		}
		old, ok := best[c.Key]
		if !ok || c.CreatedAt >= old.CreatedAt {
			best[c.Key] = c
		}
	}
	out := map[string]string{}
	if d := dryingSpec(best); d != "" {
		out["烘干"] = d
	}
	if c, ok := latestByKeys(best, "喷嘴温度范围", "喷嘴推荐温度"); ok {
		out["喷嘴"] = fmtClaim(c)
	}
	if c, ok := latestByKeys(best, "热床温度范围", "热床推荐温度"); ok {
		out["热床"] = fmtClaim(c)
	}
	if c, ok := latestByKeys(best, "打印速度上限", "打印速度范围", "打印速度"); ok {
		out["速度"] = fmtClaim(c)
	}
	if len(out) == 0 {
		return nil
	}
	return out
}
