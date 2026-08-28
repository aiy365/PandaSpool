
import re
with open('web/dist/styles.css', 'r', encoding='utf-8') as f:
    text = f.read()

old_css = '.inv-list { display: grid; gap: .75rem; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }'
new_css = '''
.inv-list { column-count: 1; column-gap: 0.75rem; }
@media (min-width: 640px) { .inv-list { column-count: 2; } }
@media (min-width: 1024px) { .inv-list { column-count: 3; } }
@media (min-width: 1280px) { .inv-list { column-count: 4; } }
@media (min-width: 1536px) { .inv-list { column-count: 5; } }
@media (min-width: 1750px) { .inv-list { column-count: 6; } }
.inv-card { break-inside: avoid; margin-bottom: 0.75rem; }
'''

text = text.replace(old_css, new_css)

with open('web/dist/styles.css', 'w', encoding='utf-8') as f:
    f.write(text)

