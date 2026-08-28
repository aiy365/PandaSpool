
import re
with open("internal/server/notify.go", "r", encoding="utf-8") as f:
    text = f.read()

old_payload = """				payload := map[string]any{
					"touser":  toUser,
					"msgtype": "news",
					"agentid": agentId,
					"news": map[string]any{
						"articles": []map[string]any{
							{
								"title":       title,
								"description": desc,
								"url":         "https://3d.bstccc.cn/#/machine",
								"picurl":      picUrl,
							},
						},
					},
				}"""

new_payload = """				var payload map[string]any
				if picUrl != "" {
					payload = map[string]any{
						"touser":  toUser,
						"msgtype": "news",
						"agentid": agentId,
						"news": map[string]any{
							"articles": []map[string]any{
								{
									"title":       title,
									"description": desc,
									"url":         "https://3d.bstccc.cn/#/machine",
									"picurl":      picUrl,
								},
							},
						},
					}
				} else {
					payload = map[string]any{
						"touser":  toUser,
						"msgtype": "textcard",
						"agentid": agentId,
						"textcard": map[string]any{
							"title":       title,
							"description": desc,
							"url":         "https://3d.bstccc.cn/#/machine",
							"btntxt":      "查看详情",
						},
					}
				}"""

text = text.replace(old_payload, new_payload)

with open("internal/server/notify.go", "w", encoding="utf-8") as f:
    f.write(text)

