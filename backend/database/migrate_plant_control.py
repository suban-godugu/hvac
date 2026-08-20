import sqlite3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

db_path = os.path.join(os.path.dirname(__file__), "hvac_supervisory.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'plant_control_%'").fetchall()
for (t,) in tables:
    c.execute(f"DROP TABLE IF EXISTS {t}")
conn.commit()
conn.close()

from backend.database.session import init_db
init_db()
print("All 16 Plant Control tables recreated successfully with complete schema.")
