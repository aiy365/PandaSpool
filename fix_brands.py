
import sqlite3
conn = sqlite3.connect("data/app.sqlite3")
cur = conn.cursor()

cur.execute("UPDATE products SET brand=\"遇果\" WHERE brand IN (\"淘工厂\", \"天天特卖工厂\", \"遇果科技\")")
cur.execute("UPDATE products SET brand=\"三绿\" WHERE brand=\"三绿SUNLU\"")

conn.commit()
print("Brands fixed")

