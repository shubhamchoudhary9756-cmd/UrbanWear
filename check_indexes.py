"""
Temporary script — verify database indexes
"""
import sqlite3
import os

db_path = os.path.join("instance", "database.db")

if not os.path.exists(db_path):
    print(f"❌ Database not found at: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='index' AND name LIKE 'idx_%'
    ORDER BY name
""")

indexes = cur.fetchall()

print("\n📋 Indexes in database:\n")
for idx in indexes:
    print(f"  ✅ {idx[0]}")

print(f"\n✅ Total: {len(indexes)} indexes\n")

conn.close()