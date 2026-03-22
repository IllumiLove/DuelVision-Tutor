"""
Sync Chinese card names from YGOCDB into local database.
Uses async concurrency to speed up API calls.
"""
import asyncio
import sqlite3
import sys
import time
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DATA_DIR

DB_PATH = DATA_DIR / "cards.db"
YGOCDB_API = "https://ygocdb.com/api/v0/"
CONCURRENCY = 10  # max parallel requests
DELAY = 0.05  # delay between batches


async def fetch_chinese_name(client: httpx.AsyncClient, card_id: int) -> dict | None:
    """Fetch Chinese name for a card by ID from YGOCDB."""
    try:
        r = await client.get(f"{YGOCDB_API}?search={card_id}")
        data = r.json()
        result = data.get("result", [])
        if result:
            c = result[0]
            # Verify it's the same card by checking ID
            if c.get("id") == card_id:
                return {
                    "id": card_id,
                    "cn_name": c.get("cn_name", ""),
                    "md_name": c.get("md_name", ""),
                    "desc_cn": c.get("text", {}).get("desc", ""),
                }
    except Exception:
        pass
    return None


async def sync_chinese_names():
    """Fetch Chinese names for all cards in our database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Get all card IDs that don't have Chinese names yet
    cur = conn.execute("SELECT id, name_en FROM cards WHERE name_zh = '' OR name_zh IS NULL")
    cards = cur.fetchall()
    total = len(cards)
    print(f"Found {total} cards without Chinese names")

    if total == 0:
        print("All cards already have Chinese names!")
        conn.close()
        return

    updated = 0
    failed = 0
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def fetch_with_limit(client, card_id):
        async with semaphore:
            result = await fetch_chinese_name(client, card_id)
            await asyncio.sleep(DELAY)
            return result

    async with httpx.AsyncClient(timeout=15) as client:
        batch_size = 50
        for i in range(0, total, batch_size):
            batch = cards[i:i + batch_size]
            tasks = [fetch_with_limit(client, row["id"]) for row in batch]
            results = await asyncio.gather(*tasks)

            update_rows = []
            for result in results:
                if result and (result["cn_name"] or result["md_name"]):
                    # Prefer md_name (Master Duel specific) over cn_name
                    name_zh = result["md_name"] or result["cn_name"]
                    desc_zh = result["desc_cn"] or ""
                    update_rows.append((name_zh, desc_zh, result["id"]))
                    updated += 1
                else:
                    failed += 1

            if update_rows:
                conn.executemany(
                    "UPDATE cards SET name_zh = ?, description_zh = ? WHERE id = ?",
                    update_rows,
                )
                conn.commit()

            progress = min(i + batch_size, total)
            pct = progress / total * 100
            print(f"  [{progress}/{total}] ({pct:.0f}%) updated={updated}, missed={failed}", end="\r")

    print(f"\nDone! Updated: {updated}, Missed: {failed}, Total: {total}")

    # Show stats
    cur = conn.execute("SELECT COUNT(*) FROM cards WHERE name_zh != '' AND name_zh IS NOT NULL")
    count_zh = cur.fetchone()[0]
    cur = conn.execute("SELECT COUNT(*) FROM cards")
    count_total = cur.fetchone()[0]
    print(f"Database: {count_zh}/{count_total} cards have Chinese names")

    conn.close()


if __name__ == "__main__":
    t0 = time.time()
    asyncio.run(sync_chinese_names())
    print(f"Elapsed: {time.time() - t0:.1f}s")
