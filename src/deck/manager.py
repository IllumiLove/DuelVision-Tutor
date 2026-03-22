from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from loguru import logger
from src.config import DECKS_DIR


class DeckManager:
    """Manage user deck lists."""

    def __init__(self, decks_dir: Path | None = None):
        self.decks_dir = decks_dir or DECKS_DIR
        self.decks_dir.mkdir(parents=True, exist_ok=True)

    def save_deck(
        self,
        name: str,
        main_deck: list[str],
        extra_deck: list[str] | None = None,
        side_deck: list[str] | None = None,
    ):
        """Save a deck to JSON file."""
        deck = {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "main_deck": main_deck,
            "extra_deck": extra_deck or [],
            "side_deck": side_deck or [],
        }
        path = self.decks_dir / f"{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(deck, f, ensure_ascii=False, indent=2)
        logger.info(f"Deck saved: {path}")

    def load_deck(self, name: str) -> dict | None:
        """Load a deck by name."""
        path = self.decks_dir / f"{name}.json"
        if not path.exists():
            logger.warning(f"Deck not found: {path}")
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_decks(self) -> list[str]:
        """List all saved deck names."""
        return [p.stem for p in self.decks_dir.glob("*.json")]

    def get_deck_text(self, name: str) -> str:
        """Get deck as text for LLM prompt."""
        deck = self.load_deck(name)
        if not deck:
            return ""
        lines = [f"【卡組: {deck['name']}】"]
        lines.append(f"主牌組 ({len(deck['main_deck'])}張): {', '.join(deck['main_deck'])}")
        if deck.get("extra_deck"):
            lines.append(f"額外牌組 ({len(deck['extra_deck'])}張): {', '.join(deck['extra_deck'])}")
        return "\n".join(lines)
