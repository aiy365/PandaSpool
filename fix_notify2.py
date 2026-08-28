
import re
with open("internal/server/notify.go", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Fix the layer logic to trigger on layer 2 (first layer finished)
old_layer_logic = """	shouldNotifyLayer1 := false
	if !s.notifiedLayer1 && endedAt.IsZero() && (gcode == "PREPARE" || gcode == "RUNNING") && layerVal != "0" {
		s.notifiedLayer1 = true
		shouldNotifyLayer1 = true
	}"""
new_layer_logic = """	shouldNotifyLayer1 := false
	if !s.notifiedLayer1 && endedAt.IsZero() && (gcode == "PREPARE" || gcode == "RUNNING") && layerVal != "0" && layerVal != "1" {
		// If layer is 2 or higher, it means layer 1 has finished
		s.notifiedLayer1 = true
		shouldNotifyLayer1 = true
	}"""
text = text.replace(old_layer_logic, new_layer_logic)

# Change the title to reflect "First layer finished" instead of "started"
text = text.replace("🚀 打印任务 - 首层已开始！", "🚀 打印任务 - 首层已完成！")

# 2. Fix the WeCom payload URL for picUrl
old_wecom_payload = """								"url":         "https://3d.bstccc.cn/#/machine",
								"picurl":      picUrl,"""
new_wecom_payload = """								"url":         picUrl,
								"picurl":      picUrl,"""
text = text.replace(old_wecom_payload, new_wecom_payload)

with open("internal/server/notify.go", "w", encoding="utf-8") as f:
    f.write(text)

