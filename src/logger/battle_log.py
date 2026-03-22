from __future__ import annotations

import json
import time
from pathlib import Path
from datetime import datetime

from loguru import logger as log
from src.config import LOGS_DIR


class BattleLogger:
    """Log battle states and AI advice."""

    def __init__(self, logs_dir: Path | None = None, max_matches: int = 100):
        self.logs_dir = logs_dir or LOGS_DIR
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.max_matches = max_matches
        self._current_match_id: str | None = None
        self._current_file: Path | None = None

    def start_match(self):
        """Start recording a new match."""
        self._current_match_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self._current_file = self.logs_dir / f"match_{self._current_match_id}.jsonl"
        log.info(f"Battle log started: {self._current_match_id}")

    def log_state(self, turn: int, phase: str, game_state: dict, ai_suggestion: dict | None = None):
        """Log a game state entry."""
        if not self._current_file:
            self.start_match()

        entry = {
            "match_id": self._current_match_id,
            "timestamp": time.time(),
            "turn": turn,
            "phase": phase,
            "game_state": game_state,
            "ai_suggestion": ai_suggestion,
        }

        with open(self._current_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def end_match(self):
        """End current match recording."""
        log.info(f"Battle log ended: {self._current_match_id}")
        self._current_match_id = None
        self._current_file = None
        self._cleanup_old_logs()

    def _cleanup_old_logs(self):
        """Remove oldest logs if exceeding max_matches."""
        logs = sorted(self.logs_dir.glob("match_*.jsonl"))
        while len(logs) > self.max_matches:
            oldest = logs.pop(0)
            oldest.unlink()
            log.debug(f"Removed old log: {oldest.name}")

    def get_recent_history(self, n: int = 3) -> str:
        """Get summary of recent matches for LLM context."""
        logs = sorted(self.logs_dir.glob("match_*.jsonl"), reverse=True)[:n]
        if not logs:
            return ""

        summaries = []
        for log_file in logs:
            entries = []
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
            if entries:
                first = entries[0]
                summary = f"- 對戰 {first['match_id']}: {len(entries)} 回合紀錄"
                summaries.append(summary)

        return "\n".join(summaries) if summaries else ""
