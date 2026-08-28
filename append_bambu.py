
with open("internal/bambu/bambu.go", "a", encoding="utf-8") as f:
    f.write("""

// SetFilament is added for testing MQTT filament assignment
func (c *Client) SetFilament(amsId, trayId int, infoIdx, color, matType string) error {
	c.mu.RLock()
	cli := c.mqtt
	sn := c.sn
	c.mu.RUnlock()
	if cli == nil {
		return fmt.Errorf("mqtt not connected")
	}
	topic := fmt.Sprintf("device/%s/request", sn)
	
	payload := fmt.Sprintf(` + "`" + `{"print":{"sequence_id":"999","command":"ami_assign_info","ams_id":%d,"tray_id":%d,"tray_info_idx":"%s","tray_color":"%s","nozzle_temp_min":230,"nozzle_temp_max":260,"tray_type":"%s"}}` + "`" + `, amsId, trayId, infoIdx, color, matType)
	tok := cli.Publish(topic, 0, false, payload)
	tok.Wait()
	return tok.Error()
}
""")

