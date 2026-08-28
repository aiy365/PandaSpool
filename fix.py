import re

with open('live_app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Make Material Cards use a grid layout instead of vertical stacking
# Change id="list" to id="list" class="materials-grid mt-4" in viewMaterials
content = content.replace('<div id="list" class="mt-4"></div>', '<div id="list" class="materials-grid mt-4"></div>')
# Wait, let's see how #list is defined.
# If we can't find it precisely, let's just use CSS `.materials-grid`
