import re
with open('web/dist/styles.css', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('.settings-head > div { flex: 1; }', '.settings-head > div { flex: 0 1 auto; margin-right: auto; }')

with open('web/dist/styles.css', 'w', encoding='utf-8') as f:
    f.write(content)
