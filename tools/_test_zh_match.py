"""Verify Chinese card name matching works correctly."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.card_db import CardDB

db = CardDB()
db.connect()

print(f"Card DB: {db.card_count} total cards")
print(f"Chinese names loaded: {len(db._card_names_zh)}")
print(f"English names loaded: {len(db._card_names_en)}")

# Test fuzzy match with Chinese names (simulating OCR results)
test_cases = [
    "灰流丽",        # Ash Blossom
    "增殖的G",       # Maxx "C"
    "青眼白龙",      # Blue-Eyes White Dragon
    "蛇眼灰烬",      # Snake-Eye Ash (might differ)
    "效果遮蒙者",    # Effect Veiler
    "无限泡影",      # Infinite Impermanence
    "灰流丽",        # Ash Blossom (exact)
    "墓穴的指名者",  # Called by the Grave
]

print("\n=== Fuzzy Match Tests ===")
for text in test_cases:
    result = db.fuzzy_match(text)
    info = db.get_card_info(result) if result else None
    en_name = info.get("name_en", "?") if info else "?"
    print(f"  '{text}' -> '{result}' ({en_name})")

# Also test get_card_effect with Chinese name
print("\n=== Card Effect Test ===")
effect = db.get_card_effect("灰流丽")
print(f"灰流丽 effect: {effect[:100]}..." if effect else "No effect found")

db.close()
