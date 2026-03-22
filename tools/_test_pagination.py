"""Test pagination strategy to collect all YGOCDB cards."""
import httpx
import time

# Count total pages with wildcard search
print("Counting total cards via pagination...")
total = 0
nxt = 0
pages = 0
while True:
    url = f"https://ygocdb.com/api/v0/?search=.&next={nxt}"
    r = httpx.get(url, timeout=30)
    data = r.json()
    result = data.get("result", [])
    new_next = data.get("next", None)
    total += len(result)
    pages += 1
    
    if pages <= 3 or pages % 50 == 0:
        print(f"  Page {pages}: +{len(result)} cards (total={total}), next={new_next}")
    
    if not result or new_next is None or new_next == nxt:
        break
    nxt = new_next
    time.sleep(0.1)  # Be polite

print(f"\nTotal: {total} cards across {pages} pages")
