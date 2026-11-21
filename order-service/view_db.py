import sqlite3

conn = sqlite3.connect("orders.db")

rows = conn.execute(
    "SELECT * FROM orders"
).fetchall()

for row in rows:
    print(row)

conn.close()