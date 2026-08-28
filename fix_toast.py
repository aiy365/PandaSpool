import re

with open('live_app.js', 'r', encoding='utf-8') as f:
    content = f.read()

old_toast = 'toast(`成功入库 ${qty} 盘！短编号: ${codes}`, "success");'
new_toast = 'toast(`成功处理入库申请。`, "success");'

content = content.replace(old_toast, new_toast)

with open('live_app.js', 'w', encoding='utf-8') as f:
    f.write(content)
