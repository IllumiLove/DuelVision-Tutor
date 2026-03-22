from __future__ import annotations

import httpx
from loguru import logger

API_BASE = "https://db.ygoprodeck.com/api/v7"


async def fetch_all_cards() -> list[dict]:
    """Fetch all card data from YGOProDeck API."""
    url = f"{API_BASE}/cardinfo.php"
    logger.info("Fetching all cards from YGOProDeck API...")

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    cards = data.get("data", [])
    logger.info(f"Fetched {len(cards)} cards from API")

    result = []
    for c in cards:
        result.append({
            "id": c.get("id"),
            "name_en": c.get("name", ""),
            "name_zh": "",
            "card_type": c.get("type", ""),
            "sub_type": c.get("race", ""),
            "attribute": c.get("attribute", ""),
            "race": c.get("race", ""),
            "level": c.get("level", 0),
            "atk": c.get("atk", 0),
            "def_": c.get("def", 0),
            "description_en": c.get("desc", ""),
            "description_zh": "",
            "archetype": c.get("archetype", ""),
        })
    return result


async def sync_database(card_db):
    """Download all cards and sync to local database."""
    cards = await fetch_all_cards()
    card_db.upsert_cards(cards)
    logger.info(f"Database synced: {card_db.card_count} cards total")
