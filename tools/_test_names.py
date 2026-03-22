import httpx
import json

cards_to_check = ["89631139", "44508094", "14558127", "59438930"]
for cid in cards_to_check:
    r = httpx.get(f"https://ygocdb.com/api/v0/?search={cid}", timeout=15)
    data = r.json()
    result = data.get("result", [])
    if result:
        c = result[0]
        en = c.get("en_name", "?")
        cn = c.get("cn_name", "")
        sc = c.get("sc_name", "")
        md = c.get("md_name", "")
        print(f"{en}")
        print(f"  cn_name: {cn}")
        print(f"  sc_name: {sc}")
        print(f"  md_name: {md}")
        print()
