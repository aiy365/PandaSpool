import re

with open('web/dist/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Rewrite swRow
swRow_new = '''function swRow(label, role) {
  return \<div class=\
