with open('internal/server/server.go', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('WHERE c.status = \\\
