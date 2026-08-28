import re

with open('live_app.js', 'r', encoding='utf-8') as f:
    content = f.read()

old_card = '`<section class="card bg-base-100 shadow-sm border border-base-300 break-inside-avoid mb-4">${inner.includes("card-body") ? inner : `<div class="card-body">${inner}</div>`}</section>`'
new_card = '`<section class="card bg-base-100 shadow-sm border border-base-300 break-inside-avoid mb-4">${inner.includes("card-body") ? inner : `<div class="card-body p-4 sm:p-6">${inner}</div>`}</section>`'
content = content.replace(old_card, new_card)

with open('live_app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Optimized card padding for mobile.")
