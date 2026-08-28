
import re

with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

# Replace the mocked s.compare
text = re.sub(
    r"func \(s \*Server\) compare\(w http\.ResponseWriter, r \*http\.Request\) \{.*?\}",
    """func (s *Server) compare(w http.ResponseWriter, r *http.Request) {
\tres := map[string][]map[string]any{}
\trows, err := s.st.DB.Query(`
\t\tSELECT p.name, c.source, c.claim_key, c.claim_value, c.unit
\t\tFROM claims c JOIN products p ON c.product_id = p.id
\t\tWHERE c.status = 'confirmed'
\t`)
\tif err == nil {
\t\tdefer rows.Close()
\t\tfor rows.Next() {
\t\t\tvar product, source, key, value, unit string
\t\t\trows.Scan(&product, &source, &key, &value, &unit)
\t\t\tres[key] = append(res[key], map[string]any{
\t\t\t\t"product": product,
\t\t\t\t"source": source,
\t\t\t\t"value": value,
\t\t\t\t"unit": unit,
\t\t\t})
\t\t}
\t}
\tjson.NewEncoder(w).Encode(res)
}""",
    text
)

# Replace applyIntegrations
text = re.sub(
    r"func \(s \*Server\) applyIntegrations\(\)\s*\{\s*\}",
    """func (s *Server) applyIntegrations() {
\tcfg := s.st.LoadSettings()
\ts.bambu.Configure(cfg.Bambu.Region, cfg.Bambu.Account, cfg.Bambu.Password, cfg.Bambu.PrinterSN, cfg.Bambu.AccessToken)
\ts.bambu.Reconnect()
\ts.ew.Configure(ewelink.Config{
\t\tRegion:       cfg.EWeLink.Region,
\t\tAccount:      cfg.EWeLink.Account,
\t\tPassword:     cfg.EWeLink.Password,
\t\tAppID:        cfg.EWeLink.AppID,
\t\tAppSecret:    cfg.EWeLink.AppSecret,
\t\tAccessToken:  cfg.EWeLink.AccessToken,
\t\tRefreshToken: cfg.EWeLink.RefreshToken,
\t})
\ts.ez.Configure(cfg.Ezviz.AppKey, cfg.Ezviz.AppSecret)
}""",
    text
)

# Replace automate
text = re.sub(
    r"func \(s \*Server\) automate\(\)\s*\{\s*\}",
    """func (s *Server) automate() {
\tfor {
\t\ttime.Sleep(10 * time.Second)
\t\tcfg := s.st.LoadSettings()
\t\tif cfg.Automations.PrintBoostMinutes > 0 && cfg.EWeLink.BoxPrint != "" {
\t\t\tprintingOrBoost := s.bambu.PrintingOrBoost(cfg.Automations.PrintBoostMinutes)
\t\t\ts.ew.Switch(cfg.EWeLink.BoxPrint, printingOrBoost)
\t\t}
\t\tif cfg.EWeLink.BoxAlways != "" {
\t\t\ts.ew.Switch(cfg.EWeLink.BoxAlways, cfg.Automations.BoxAlwaysOn)
\t\t}
\t}
}""",
    text
)

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

