with open('web/dist/stock-matrix.js', 'r', encoding='utf-8') as f:
    js = f.read()
if "黑灰色系" in js:
    print("Successfully replaced.")
else:
    print("Not replaced!")
