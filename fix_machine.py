
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

# Add ezviz status to machine payload
text = text.replace(
    "\"air\":      airMap,",
    "\"air\":      airMap,\n\t\t\"ezviz\":    s.ez.Status(),"
)

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

