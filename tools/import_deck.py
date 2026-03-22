"""
DuelVision Tutor - 牌組匯入工具

使用方式:
  1. 互動模式: python tools/import_deck.py
  2. 從文字檔匯入: python tools/import_deck.py --file 牌組.txt
  3. 從 YDK 檔匯入: python tools/import_deck.py --ydk 牌組.ydk

文字檔格式 (每行一張卡，可加數量):
  3 Ash Blossom & Joyous Spring
  2 Effect Veiler
  1 Dark Magician
  
  # 以 --- 或 [extra] 分隔額外牌組
  ---
  1 Accesscode Talker
"""
from __future__ import annotations

import sys
import json
import re
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DECKS_DIR
from src.database.card_db import CardDB


def parse_card_line(line: str) -> tuple[int, str]:
    """Parse a card line. Supported formats:
      3 Ash Blossom          (number first)
      3x Ash Blossom         (number+x first)
      Ash Blossom x3         (x+number after)
      魔轰神鲁力 3           (name then number, Chinese friendly)
      魔轰神鲁力             (no number = 1)
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return 0, ""

    # Format: "3 Card Name" or "3x Card Name"
    m = re.match(r"^(\d+)\s*[xX]?\s+(.+)$", line)
    if m:
        return int(m.group(1)), m.group(2).strip()

    # Format: "Card Name x3"
    m = re.match(r"^(.+?)\s*[xX]\s*(\d+)$", line)
    if m:
        return int(m.group(2)), m.group(1).strip()

    # Format: "Card Name 3" (name followed by a standalone number at end)
    m = re.match(r"^(.+?)\s+(\d+)$", line)
    if m:
        return int(m.group(2)), m.group(1).strip()

    # Just a card name (count=1)
    return 1, line


def parse_text_deck(text: str) -> tuple[list[str], list[str]]:
    """Parse text format deck into (main_deck, extra_deck)."""
    main_deck = []
    extra_deck = []
    current = main_deck

    for line in text.strip().splitlines():
        line = line.strip()

        # Section separators
        if line in ("---", "===") or line.lower() in ("[extra]", "[extra deck]", "#extra", "# extra"):
            current = extra_deck
            continue

        count, name = parse_card_line(line)
        if count > 0 and name:
            for _ in range(count):
                current.append(name)

    return main_deck, extra_deck


def parse_ydk_file(path: Path, card_db: CardDB) -> tuple[list[str], list[str], list[str]]:
    """Parse YDK file (card IDs) into card names."""
    main_deck = []
    extra_deck = []
    side_deck = []
    current = main_deck

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or line.startswith("!"):
                if "extra" in line.lower():
                    current = extra_deck
                elif "side" in line.lower():
                    current = side_deck
                continue
            if not line or not line.isdigit():
                continue

            card_id = int(line)
            info = card_db.get_card_by_id(card_id)
            if info:
                current.append(info.get("name_zh") or info.get("name_en", f"ID:{card_id}"))
            else:
                current.append(f"Unknown(ID:{card_id})")

    return main_deck, extra_deck, side_deck


def interactive_mode(card_db: CardDB):
    """Interactive deck creation."""
    print("\n" + "=" * 50)
    print("  DuelVision Tutor - 牌組建立工具")
    print("=" * 50)

    name = input("\n牌組名稱: ").strip()
    if not name:
        print("未輸入名稱，取消。")
        return

    print("\n請貼上你的主牌組卡名（每行一張卡，可加數量如 '3 Ash Blossom'）")
    print("輸入完成後，輸入空行然後打 'done'")
    print("-" * 40)

    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip().lower() == "done":
            break
        lines.append(line)

    text = "\n".join(lines)
    main_deck, extra_deck = parse_text_deck(text)

    if not main_deck:
        print("未偵測到卡片，取消。")
        return

    # Fuzzy match card names
    print(f"\n偵測到 {len(main_deck)} 張主牌組 + {len(extra_deck)} 張額外牌組")
    print("正在比對卡名...")

    main_matched = match_cards(main_deck, card_db)
    extra_matched = match_cards(extra_deck, card_db)

    # Show result
    print(f"\n{'=' * 40}")
    print(f"牌組: {name}")
    print(f"主牌組 ({len(main_matched)} 張):")
    for card in sorted(set(main_matched)):
        count = main_matched.count(card)
        print(f"  {count}x {card}")

    if extra_matched:
        print(f"\n額外牌組 ({len(extra_matched)} 張):")
        for card in sorted(set(extra_matched)):
            count = extra_matched.count(card)
            print(f"  {count}x {card}")

    # Save
    confirm = input("\n儲存這個牌組？(y/n): ").strip().lower()
    if confirm in ("y", "yes", ""):
        save_deck(name, main_matched, extra_matched)
        print(f"已儲存至 data/decks/{name}.json")
    else:
        print("取消儲存。")


def match_cards(cards: list[str], card_db: CardDB) -> list[str]:
    """Match card names against database."""
    matched = []
    for card in cards:
        result = card_db.fuzzy_match(card, score_cutoff=50)
        if result:
            matched.append(result)
        else:
            matched.append(card)  # Keep original if no match
            print(f"  ⚠ 未匹配: {card}")
    return matched


def save_deck(name: str, main_deck: list[str], extra_deck: list[str], side_deck: list[str] | None = None):
    """Save deck to JSON."""
    from src.deck.manager import DeckManager
    dm = DeckManager()
    dm.save_deck(name, main_deck, extra_deck, side_deck or [])


def main():
    import argparse
    parser = argparse.ArgumentParser(description="DuelVision Tutor 牌組匯入工具")
    parser.add_argument("--file", "-f", help="從文字檔匯入 (每行一張卡)")
    parser.add_argument("--ydk", help="從 YDK 檔匯入")
    parser.add_argument("--name", "-n", help="牌組名稱")
    args = parser.parse_args()

    card_db = CardDB()
    card_db.connect()
    print(f"卡牌資料庫: {card_db.card_count} 張卡")

    if args.ydk:
        path = Path(args.ydk)
        if not path.exists():
            print(f"找不到檔案: {path}")
            return
        name = args.name or path.stem
        main_deck, extra_deck, side_deck = parse_ydk_file(path, card_db)
        main_matched = match_cards(main_deck, card_db)
        extra_matched = match_cards(extra_deck, card_db)
        side_matched = match_cards(side_deck, card_db)
        save_deck(name, main_matched, extra_matched, side_matched)
        print(f"已匯入: {name} (主{len(main_matched)}張 / 額外{len(extra_matched)}張 / 副{len(side_matched)}張)")

    elif args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"找不到檔案: {path}")
            return
        name = args.name or path.stem
        text = path.read_text(encoding="utf-8")
        main_deck, extra_deck = parse_text_deck(text)
        main_matched = match_cards(main_deck, card_db)
        extra_matched = match_cards(extra_deck, card_db)
        save_deck(name, main_matched, extra_matched)
        print(f"已匯入: {name} (主{len(main_matched)}張 / 額外{len(extra_matched)}張)")

    else:
        interactive_mode(card_db)

    card_db.close()


if __name__ == "__main__":
    main()
