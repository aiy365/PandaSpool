import re
import sys

with open('C:/work/3D模型/printpilot-hub/web/src/App.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'(<table className="table">.*?</table>)', r'<div className="table-wrap">\1</div>', content, flags=re.DOTALL)

with open('C:/work/3D模型/printpilot-hub/web/src/App.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
