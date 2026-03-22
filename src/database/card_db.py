from __future__ import annotations

import sqlite3
from pathlib import Path

from loguru import logger
from rapidfuzz import process, fuzz

from src.config import DATA_DIR

DB_PATH = DATA_DIR / "cards.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_zh TEXT DEFAULT '',
    card_type TEXT DEFAULT '',
    sub_type TEXT DEFAULT '',
    attribute TEXT DEFAULT '',
    race TEXT DEFAULT '',
    level INTEGER DEFAULT 0,
    atk INTEGER DEFAULT 0,
    def_ INTEGER DEFAULT 0,
    description_en TEXT DEFAULT '',
    description_zh TEXT DEFAULT '',
    archetype TEXT DEFAULT '',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cards_name_zh ON cards(name_zh);
CREATE INDEX IF NOT EXISTS idx_cards_name_en ON cards(name_en);
CREATE INDEX IF NOT EXISTS idx_cards_archetype ON cards(archetype);
"""


class CardDB:
    """Local SQLite card database."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self._conn: sqlite3.Connection | None = None
        self._card_names_zh: list[str] = []
        self._card_names_en: list[str] = []

    def connect(self):
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(CREATE_TABLE_SQL)
        self._load_name_cache()
        logger.info(
            f"Card DB connected: {self.db_path} "
            f"({len(self._card_names_zh)} zh, {len(self._card_names_en)} en)"
        )

    def _load_name_cache(self):
        """Load card names into memory for fuzzy matching."""
        cur = self._conn.execute("SELECT name_zh, name_en FROM cards")
        self._card_names_zh = []
        self._card_names_en = []
        for row in cur:
            if row["name_zh"]:
                self._card_names_zh.append(row["name_zh"])
            if row["name_en"]:
                self._card_names_en.append(row["name_en"])

    def fuzzy_match(self, text: str, score_cutoff: int = 60) -> str | None:
        """Fuzzy match OCR text to a card name."""
        if not text or len(text) < 2:
            return None

        # Try Chinese names first
        if self._card_names_zh:
            result = process.extractOne(
                text, self._card_names_zh, scorer=fuzz.WRatio, score_cutoff=score_cutoff
            )
            if result:
                return result[0]

        # Then English
        if self._card_names_en:
            result = process.extractOne(
                text, self._card_names_en, scorer=fuzz.WRatio, score_cutoff=score_cutoff
            )
            if result:
                return result[0]

        return None

    def get_card_info(self, name: str) -> dict | None:
        """Get full card info by name (zh or en)."""
        cur = self._conn.execute(
            "SELECT * FROM cards WHERE name_zh = ? OR name_en = ? LIMIT 1",
            (name, name),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_card_by_id(self, card_id: int) -> dict | None:
        """Get card info by card ID."""
        cur = self._conn.execute("SELECT * FROM cards WHERE id = ? LIMIT 1", (card_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_card_effect(self, name: str) -> str:
        """Get card effect description for LLM prompt, including level/stats and trigger annotations."""
        info = self.get_card_info(name)
        if not info:
            return ""
        desc = info.get("description_zh") or info.get("description_en") or ""
        card_type = info.get("card_type", "")
        parts = [f"【{name}】{card_type}"]
        # Add level/rank info for monsters
        level = info.get("level", 0)
        if level and "Monster" in card_type:
            if "XYZ" in info.get("sub_type", ""):
                parts.append(f"階級{level}")
            elif "Link" in info.get("sub_type", ""):
                parts.append(f"LINK-{level}")
            else:
                parts.append(f"★{level}")
                if level >= 5:
                    parts.append("(需要祭品通召)")
        # ATK/DEF
        atk = info.get("atk", 0)
        def_ = info.get("def_", 0)
        if "Monster" in card_type:
            parts.append(f"ATK:{atk}/DEF:{def_}")
        # Attribute/Race
        attr = info.get("attribute", "")
        race = info.get("race", "")
        if attr:
            parts.append(attr)
        if race:
            parts.append(race)

        # Auto-annotate key trigger conditions so LLM can spot them instantly
        annotations = self._extract_annotations(desc, card_type)
        if annotations:
            parts.append("[" + "; ".join(annotations) + "]")

        parts.append(f"- {desc}")
        return " ".join(parts)

    @staticmethod
    def _extract_annotations(desc: str, card_type: str) -> list[str]:
        """Extract key gameplay annotations from card description text."""
        import re
        annotations = []
        desc_lower = desc.lower()

        # Summoning restrictions
        if "不能通常召唤" in desc or "不能通常召喚" in desc or "cannot be normal summon" in desc_lower:
            annotations.append("不能通常召喚")
        if "不能特殊召唤" in desc or "不能特殊召喚" in desc:
            annotations.append("不能特殊召喚")

        # Effect trigger conditions — must be about THIS CARD's summon, not other monsters
        # Pattern: "这张卡特殊召唤成功" = this card needs special summon to trigger
        # NOT: "这个效果特殊召唤成功" = refers to monster summoned by the effect
        has_ss_trigger = bool(
            re.search(r"这张卡特殊召[唤喚]成功", desc)
            or "if this card is special summoned" in desc_lower
            or "when this card is special summoned" in desc_lower
        )
        has_ns_trigger = bool(
            re.search(r"这张卡通常召[唤喚]成功", desc)
            or "if this card is normal summoned" in desc_lower
        )
        # Generic "这张卡召唤成功" (not preceded by 特殊/通常) = both normal & special work
        has_generic_trigger = bool(
            re.search(r"这张卡(?!特殊|通常)召[唤喚]成功", desc)
            or re.search(r"this card is (?:normal or special )?summoned", desc_lower)
        )

        if has_ss_trigger and not has_ns_trigger and not has_generic_trigger:
            annotations.append("效果觸發:需要特殊召喚成功,通常召喚不觸發!")
        elif has_ns_trigger and not has_ss_trigger:
            annotations.append("效果觸發:通常召喚成功")
        elif has_generic_trigger or (has_ss_trigger and has_ns_trigger):
            annotations.append("效果觸發:召喚成功(通召或特召皆可)")

        # Self-special summon from hand
        if ("从手卡特殊召唤" in desc or "從手牌特殊召喚" in desc
                or "special summon this card from your hand" in desc_lower):
            annotations.append("可從手牌特殊召喚自身")
        # Self-special summon from GY
        if re.search(r"这张卡(从墓地)?特殊召[唤喚]", desc) and "墓地" in desc:
            # Must be about self-reviving, not summoning other monsters
            if re.search(r"(这张卡特殊召[唤喚]|这张卡从墓地)", desc):
                # Verify it's self-revival by checking context
                if "这张卡在墓地存在" in desc or "这张卡从墓地" in desc:
                    annotations.append("可從墓地特殊召喚自身")

        # Quick effect / hand trap
        if "对方回合" in desc and "也能发动" in desc:
            annotations.append("速攻效果(對方回合可發動)")
        if "从手卡丢弃" in desc or "從手牌丟棄" in desc:
            if "Monster" in card_type:
                annotations.append("可從手牌丟棄發動(手坑)")

        # Cost indicators
        if "支付" in desc and ("基本分" in desc or "LP" in desc_lower):
            annotations.append("需支付LP")

        # Once per turn
        if "1回合只能使用1次" in desc or "各能使用1次" in desc or "you can only use" in desc_lower:
            annotations.append("每回合1次")

        return annotations

    def upsert_cards(self, cards: list[dict]):
        """Insert or update cards in batch."""
        sql = """
        INSERT OR REPLACE INTO cards
        (id, name_en, name_zh, card_type, sub_type, attribute, race, level, atk, def_,
         description_en, description_zh, archetype, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        rows = [
            (
                c.get("id"), c.get("name_en", ""), c.get("name_zh", ""),
                c.get("card_type", ""), c.get("sub_type", ""),
                c.get("attribute", ""), c.get("race", ""), c.get("level", 0),
                c.get("atk", 0), c.get("def_", 0),
                c.get("description_en", ""), c.get("description_zh", ""),
                c.get("archetype", ""),
            )
            for c in cards
        ]
        self._conn.executemany(sql, rows)
        self._conn.commit()
        self._load_name_cache()
        logger.info(f"Upserted {len(rows)} cards")

    @property
    def card_count(self) -> int:
        cur = self._conn.execute("SELECT COUNT(*) FROM cards")
        return cur.fetchone()[0]

    def close(self):
        if self._conn:
            self._conn.close()
