from __future__ import annotations

from pathlib import Path

from src.parser.game_state import GameState
from src.config import PROJECT_ROOT

SYSTEM_PROMPT_PATH = PROJECT_ROOT / "src" / "advisor" / "prompts" / "system.txt"


def load_system_prompt() -> str:
    """Load system prompt from file."""
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def build_user_prompt(
    state: GameState,
    deck_text: str = "",
    card_effects: list[str] | None = None,
    hand_analysis: str = "",
    history: str = "",
) -> str:
    """Build the user prompt from game state and context."""
    parts = [state.to_prompt_text()]

    if deck_text:
        parts.append(f"\n{deck_text}")

    if hand_analysis:
        parts.append(f"\n{hand_analysis}")

    if card_effects:
        parts.append("\n【手牌及關鍵卡片效果】")
        # Hand card effects first (up to 10), then deck effects (up to 30 more)
        for effect in card_effects[:40]:
            parts.append(effect)

    if history:
        parts.append(f"\n【最近對戰紀錄摘要】\n{history}")

    parts.append("\n請根據以上資訊，給出最佳行動建議（JSON 格式）。")
    parts.append("⚠️ 務必仔細閱讀每張卡的[觸發條件標註]，不要建議會失敗的操作！")

    return "\n".join(parts)
