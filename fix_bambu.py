import re
with open('internal/bambu/bambu.go', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'// SetFilament is added for testing MQTT filament assignment.*', '', text, flags=re.DOTALL)

with open('internal/bambu/bambu.go', 'w', encoding='utf-8') as f:
    f.write(text)
    f.write('''
// SetFilament is added for testing MQTT filament assignment
func (c *Client) SetFilament(amsId int, trayId int, infoIdx string, color string, matType string) error {
	c.mu.RLock()
	cli := c.mqtt
	sn := c.sn
	c.mu.RUnlock()
	if cli == nil {
		return fmt.Errorf(\
