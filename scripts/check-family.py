#!/usr/bin/env python3
import sqlite3
db = sqlite3.connect("/var/lib/printpilot/app.sqlite3")
print("latte", db.execute("select name,color_family from colors where name like '%拿铁%'").fetchall())
print("unclassified", db.execute("select name,color_family from colors where color_family='' or color_family='未分类'").fetchall())
