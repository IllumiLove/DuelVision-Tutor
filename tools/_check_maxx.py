import sqlite3
conn = sqlite3.connect("data/cards.db")
conn.row_factory = sqlite3.Row
print("=== Maxx C ===")
cur = conn.execute("SELECT id, name_en, name_zh FROM cards WHERE name_en LIKE '%Maxx%'")
for row in cur:
    print(f"  {row['id']}: {row['name_en']} -> {row['name_zh']}")
print("\n=== 增殖 ===")
cur = conn.execute("SELECT id, name_en, name_zh FROM cards WHERE name_zh LIKE '%增殖%'")
for row in cur:
    print(f"  {row['id']}: {row['name_en']} -> {row['name_zh']}")
conn.close()
