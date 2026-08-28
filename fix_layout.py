import re

with open('live_app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Make cards masonry-friendly
old_card = '`<section class="card bg-base-100 shadow-sm border border-base-300">${inner.includes("card-body") ? inner : `<div class="card-body">${inner}</div>`}</section>`'
new_card = '`<section class="card bg-base-100 shadow-sm border border-base-300 break-inside-avoid mb-4">${inner.includes("card-body") ? inner : `<div class="card-body">${inner}</div>`}</section>`'
content = content.replace(old_card, new_card)

# Update machine layout to masonry
content = content.replace('<div class="row cols-2">\n    ${card(`\n      <h2 class="card-title">机台（只读）</h2>', '<div class="columns-1 lg:columns-2 gap-4">\n    ${card(`\n      <h2 class="card-title">机台（只读）</h2>')

# Update settings layout to masonry
content = content.replace('<div class="settings-grid">', '<div class="columns-1 lg:columns-2 gap-4">')

# Let's also update the "row cols-2" in Home
content = content.replace('<div class="row cols-2">\n    ${card(`\n      <h2 class="card-title">机台</h2>', '<div class="columns-1 md:columns-2 gap-4">\n    ${card(`\n      <h2 class="card-title">机台</h2>')

with open('live_app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated grid layouts.")
