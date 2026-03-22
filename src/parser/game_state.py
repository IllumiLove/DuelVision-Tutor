from __future__ import annotations

from dataclasses import dataclass, field
from time import time


@dataclass
class FieldCard:
    name: str
    atk: int | None = None
    def_: int | None = None
    position: str = "ATK"  # "ATK", "DEF", "SET"
    zone: str = ""  # "MONSTER_1"~"MONSTER_5", "SPELL_1"~"SPELL_5"

    def to_text(self) -> str:
        parts = [self.name]
        if self.position == "SET":
            parts.append("(裡側)")
        else:
            if self.atk is not None:
                parts.append(f"ATK:{self.atk}")
            if self.def_ is not None:
                parts.append(f"DEF:{self.def_}")
            parts.append(f"({self.position}表示)")
        return " ".join(parts)


@dataclass
class GameState:
    phase: str = "UNKNOWN"  # DRAW, STANDBY, MAIN1, BATTLE, MAIN2, END
    turn_player: str = "unknown"  # "self" or "opponent"
    my_lp: int = 8000
    opp_lp: int = 8000
    my_hand: list[str] = field(default_factory=list)
    my_field: list[FieldCard] = field(default_factory=list)
    opp_field: list[FieldCard] = field(default_factory=list)
    my_graveyard: list[str] = field(default_factory=list)
    my_banished: list[str] = field(default_factory=list)
    chain_prompt: bool = False
    turn_count: int = 0
    timestamp: float = field(default_factory=time)

    def to_prompt_text(self) -> str:
        """Convert game state to a readable text for LLM prompt."""
        lines = [
            "【當前遊戲狀態】",
            f"階段：{self.phase}",
            f"回合數：{self.turn_count}",
            f"回合玩家：{'我方' if self.turn_player == 'self' else '對手'}",
            f"我方 LP：{self.my_lp}",
            f"對手 LP：{self.opp_lp}",
        ]

        if self.my_hand:
            lines.append(f"我方手牌：{', '.join(self.my_hand)}")
        else:
            lines.append("我方手牌：（無法辨識）")

        if self.my_field:
            field_texts = [c.to_text() for c in self.my_field]
            lines.append(f"我方場上：{' | '.join(field_texts)}")
        else:
            lines.append("我方場上：（空）")

        if self.opp_field:
            field_texts = [c.to_text() for c in self.opp_field]
            lines.append(f"對手場上：{' | '.join(field_texts)}")
        else:
            lines.append("對手場上：（空）")

        if self.my_graveyard:
            lines.append(f"我方墓地：{', '.join(self.my_graveyard)}")

        if self.my_banished:
            lines.append(f"我方除外：{', '.join(self.my_banished)}")

        if self.chain_prompt:
            lines.append("⚡ 目前有鏈結/效果觸發提示")

        return "\n".join(lines)
