import re
with open('web/dist/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('class=\
