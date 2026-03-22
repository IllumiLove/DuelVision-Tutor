"""Quick test of Chinese card name APIs."""
import httpx
import json

# Test YGOCDB
print("=== Testing YGOCDB API ===")
try:
    r = httpx.get("https://ygocdb.com/api/v0/?search=Blue-Eyes White Dragon", timeout=15)
    data = r.json()
    print("Top-level type:", type(data))
    print("Top-level keys:", list(data.keys()) if isinstance(data, dict) else "not dict")
    result = data.get("result", [])
    print("Result type:", type(result), "len:", len(result) if hasattr(result, '__len__') else "?")
    if isinstance(result, list) and len(result) > 0:
        first = result[0]
        print("First item type:", type(first))
        if isinstance(first, dict):
            print("Keys:", list(first.keys())[:20])
            for k in ["cn_name", "sc_name", "cnocg_n", "jp_name", "en_name", "id", "name"]:
                val = first.get(k, "N/A")
                print(f"  {k}: {val}")
    elif isinstance(result, dict):
        first_key = list(result.keys())[0]
        first = result[first_key]
        print("First item keys:", list(first.keys())[:20] if isinstance(first, dict) else str(first)[:200])
except Exception as e:
    print(f"YGOCDB error: {e}")
    import traceback; traceback.print_exc()

# Test YGOCDB full dump
print("\n=== Testing YGOCDB full dump ===")
try:
    r = httpx.get("https://ygocdb.com/api/v0/?search=89631139", timeout=15)
    data = r.json()
    result = data.get("result", [])
    if isinstance(result, list) and len(result) > 0:
        print(json.dumps(result[0], ensure_ascii=False, indent=2)[:500])
    elif isinstance(result, dict) and len(result) > 0:
        first = list(result.values())[0]
        print(json.dumps(first, ensure_ascii=False, indent=2)[:500])
except Exception as e:
    print(f"error: {e}")

# Test YGOProDeck cardinfo with misc=yes for alt names
print("\n=== Testing YGOProDeck misc ===")
try:
    r = httpx.get("https://db.ygoprodeck.com/api/v7/cardinfo.php?name=Blue-Eyes White Dragon&misc=yes", timeout=15)
    if r.status_code == 200:
        data = r.json()
        cards = data.get("data", [])
        if cards:
            c = cards[0]
            misc = c.get("misc_info", [])
            print("misc_info:", json.dumps(misc, ensure_ascii=False, indent=2)[:500] if misc else "empty")
    else:
        print(f"Status: {r.status_code}")
except Exception as e:
    print(f"error: {e}")
