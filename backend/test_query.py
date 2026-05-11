import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent / "data.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Example: Run a query
cursor.execute("SELECT * FROM items")
rows = cursor.fetchall()
for row in rows:
    print(row)

# Close the connection
conn.close()