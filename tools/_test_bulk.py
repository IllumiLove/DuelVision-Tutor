"""Test YGOCDB bulk capabilities."""
import httpx
import json

# Test 1: check if there's a bulk/all endpoint
print("=== Test bulk search ===")
r = httpx.get("https://ygocdb.com/api/v0/?search=.", timeout=30)
data = r.json()
result = data.get("result", [])
nxt = data.get("next", None)
print(f"Result count: {len(result)}, next: {nxt}")

# Check if paginated
if nxt:
    print(f"Has pagination! next={nxt}")
    r2 = httpx.get(f"https://ygocdb.com/api/v0/?search=.&next={nxt}", timeout=30)
    d2 = r2.json()
    print(f"Page 2: {len(d2.get('result', []))} results, next={d2.get('next')}")

# Test 2: check bulk JSON file
print("\n=== Test bulk JSON file ===")
try:
    r = httpx.head("https://ygocdb.com/api/v0/cards.json", timeout=10)
    print(f"cards.json: status={r.status_code}, content-length={r.headers.get('content-length', '?')}")
except:
    print("cards.json not available")

try:
    r = httpx.head("https://ygocdb.com/api/v0/all", timeout=10)
    print(f"all: status={r.status_code}")
except:
    print("all not available")
