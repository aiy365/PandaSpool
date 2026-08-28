import re
with open('internal/server/notify.go', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'\
