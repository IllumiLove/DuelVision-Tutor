"""
DuelVision Tutor - Real-time AI Duel Coach for Yu-Gi-Oh! Master Duel

Usage:
    python -m src.main
"""
from __future__ import annotations

import dataclasses
import sys
import time
import threading

from loguru import logger
from PyQt6.QtWidgets import QApplication

from src.config import load_config, PROJECT_ROOT
from src.capture.screen import capture_game
from src.capture.change_detect import ChangeDetector
from src.parser.ocr_engine import OCREngine
from src.parser.state_parser import StateParser
from src.parser.regions import CHANGE_DETECT_REGIONS, scale_regions
from src.database.card_db import CardDB
from src.advisor.engine import AdvisorEngine
from src.overlay.window import OverlayWindow
from src.logger.battle_log import BattleLogger
from src.deck.manager import DeckManager

# Configure loguru
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - {message}",
)
logger.add(
    PROJECT_ROOT / "data" / "duelvision.log",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
)


class DuelVisionTutor:
    """Main application controller."""

    def __init__(self):
        self.config = load_config()
        self.change_detector = ChangeDetector()
        self.ocr_engine = OCREngine(
            use_gpu=self.config.ocr.use_gpu,
            lang=self.config.ocr.language,
        )
        self.card_db = CardDB()
        self.card_db.connect()
        self.state_parser = StateParser(self.ocr_engine, card_matcher=self.card_db.fuzzy_match)
        self.advisor = AdvisorEngine(self.config)
        self.battle_logger = BattleLogger(max_matches=self.config.logger.max_matches)
        self.deck_manager = DeckManager()

        self._running = False
        self._scan_thread: threading.Thread | None = None
        self._current_deck_name: str | None = None
        self._window: OverlayWindow | None = None

        logger.info("DuelVision Tutor initialized")
        logger.info(f"Card DB: {self.card_db.card_count} cards loaded")

    def set_deck(self, deck_name: str):
        """Set current active deck."""
        self._current_deck_name = deck_name
        logger.info(f"Active deck: {deck_name}")

    def start(self, app: QApplication):
        """Start the tutor system."""
        self._window = OverlayWindow(
            width=self.config.overlay.width,
            height=self.config.overlay.height,
            opacity=self.config.overlay.opacity,
        )
        self._window.show()

        self._running = True
        self._scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._scan_thread.start()

        logger.info("DuelVision Tutor started!")

    def stop(self):
        """Stop the tutor system."""
        self._running = False
        if self._scan_thread:
            self._scan_thread.join(timeout=5)
        self.card_db.close()
        logger.info("DuelVision Tutor stopped")

    def _scan_loop(self):
        """Background scanning loop."""
        interval = self.config.capture.interval
        fast_interval = self.config.capture.fast_interval

        while self._running:
            try:
                t0 = time.time()

                # Capture game window
                frame, region = capture_game(self.config.capture.target_window)

                if frame is None:
                    if self._window:
                        self._window.set_waiting("🔍 尋找 Master Duel 視窗中...")
                    time.sleep(2)
                    continue

                capture_ms = (time.time() - t0) * 1000

                # Check for changes
                w = region["width"]
                h = region["height"]
                detect_regions = scale_regions(CHANGE_DETECT_REGIONS, w, h)

                if not self.change_detector.has_changed(frame, detect_regions):
                    time.sleep(interval)
                    continue

                # Parse game state
                state = self.state_parser.parse(frame, (w, h))

                # Get card effects for context — hand cards are critical
                card_effects = []
                seen = set()
                hand_card_infos = []  # For hand analysis
                # Hand cards first (highest priority)
                for card_name in state.my_hand:
                    if card_name not in seen:
                        effect = self.card_db.get_card_effect(card_name)
                        if effect:
                            card_effects.append(effect)
                        info = self.card_db.get_card_info(card_name)
                        if info:
                            hand_card_infos.append(info)
                        seen.add(card_name)
                # Field cards
                for c in state.my_field + state.opp_field:
                    if c.name not in seen:
                        effect = self.card_db.get_card_effect(c.name)
                        if effect:
                            card_effects.append(effect)
                        seen.add(c.name)
                # Key deck cards not yet seen (for combo routes)
                if self._current_deck_name:
                    deck_data = self.deck_manager.load_deck(self._current_deck_name)
                    if deck_data:
                        for card_name in deck_data.get('main_deck', []) + deck_data.get('extra_deck', []):
                            if card_name not in seen:
                                effect = self.card_db.get_card_effect(card_name)
                                if effect:
                                    card_effects.append(effect)
                                seen.add(card_name)

                # Build hand analysis — pre-compute what's legally playable
                hand_analysis = self._build_hand_analysis(hand_card_infos, state)

                # Get deck text
                deck_text = ""
                if self._current_deck_name:
                    deck_text = self.deck_manager.get_deck_text(self._current_deck_name)

                # Get history
                history = self.battle_logger.get_recent_history(self.config.logger.history_context)

                # Get AI advice
                t1 = time.time()
                advice = self.advisor.get_advice(
                    state,
                    deck_text=deck_text,
                    card_effects=card_effects,
                    hand_analysis=hand_analysis,
                    history=history,
                )
                ai_ms = (time.time() - t1) * 1000

                if advice and self._window:
                    self._window.update_advice(advice)
                    self._window.set_timing(capture_ms, ai_ms)

                # Log
                if self.config.logger.enabled:
                    state_dict = dataclasses.asdict(state)
                    self.battle_logger.log_state(
                        turn=state.turn_count,
                        phase=state.phase,
                        game_state=state_dict,
                        ai_suggestion=advice,
                    )

                time.sleep(fast_interval)

            except Exception as e:
                logger.exception(f"Scan loop error: {e}")
                time.sleep(interval)

    def _build_hand_analysis(self, hand_card_infos: list[dict], state) -> str:
        """Pre-compute which hand cards are legally playable and how."""
        if not hand_card_infos:
            return ""

        my_monster_count = len(state.my_field)
        normal_summonable = []
        cannot_normal_summon = []
        spells_traps = []
        special_summon_effects = []

        for info in hand_card_infos:
            name = info.get("name_zh") or info.get("name_en", "?")
            card_type = info.get("card_type", "")
            desc = info.get("description_zh") or info.get("description_en") or ""
            level = info.get("level", 0)

            if "Monster" not in card_type:
                # Spell/Trap
                spells_traps.append(name)
                continue

            # Check if monster can be normal summoned
            has_ns_restriction = (
                "不能通常召唤" in desc or "不能通常召喚" in desc
                or "cannot be normal summon" in desc.lower()
            )

            if has_ns_restriction:
                cannot_normal_summon.append(f"{name}(不能通常召喚)")
            elif level <= 4:
                normal_summonable.append(f"{name}(★{level})")
            elif level <= 6:
                if my_monster_count >= 1:
                    normal_summonable.append(f"{name}(★{level}, 需1祭品, 場上有{my_monster_count}怪)")
                else:
                    cannot_normal_summon.append(f"{name}(★{level}, 需1祭品但場上無怪)")
            else:
                if my_monster_count >= 2:
                    normal_summonable.append(f"{name}(★{level}, 需2祭品, 場上有{my_monster_count}怪)")
                else:
                    cannot_normal_summon.append(f"{name}(★{level}, 需2祭品但場上怪獸不足)")

            # Check for self special summon from hand
            if ("特殊召唤" in desc or "特殊召喚" in desc) and ("从手卡" in desc or "從手牌" in desc):
                special_summon_effects.append(name)
            # Check if effect requires special summon
            if "特殊召唤成功" in desc or "特殊召喚成功" in desc:
                # This card's effect only triggers on special summon
                pass  # Already annotated in card_effects

        lines = ["【手牌操作合法性分析（系統預計算，AI必須遵守）】"]
        if normal_summonable:
            lines.append(f"✅ 可通常召喚: {', '.join(normal_summonable)}")
        if cannot_normal_summon:
            lines.append(f"❌ 不能通常召喚: {', '.join(cannot_normal_summon)}")
        if spells_traps:
            lines.append(f"🃏 魔法/陷阱: {', '.join(spells_traps)}")
        if special_summon_effects:
            lines.append(f"⚡ 有手牌特召效果: {', '.join(special_summon_effects)}")
        lines.append("⚠️ 注意：有些怪獸的效果只在「特殊召喚成功」時觸發，通常召喚不會觸發！請仔細閱讀效果文本！")

        result = "\n".join(lines)
        logger.debug(f"Hand analysis:\n{result}")
        return result


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    tutor = DuelVisionTutor()

    # Check if card DB needs initial sync
    if tutor.card_db.card_count == 0:
        logger.info("Card database is empty, starting initial sync...")
        import asyncio
        from src.database.ygoprodeck import sync_database
        asyncio.run(sync_database(tutor.card_db))

    # Load active deck from config or auto-detect
    active_deck = getattr(tutor.config, 'deck_active', None)
    if not active_deck:
        # Try to read from config.yaml raw
        import yaml
        cfg_path = PROJECT_ROOT / "config.yaml"
        if cfg_path.exists():
            with open(cfg_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            active_deck = (raw.get("deck") or {}).get("active", "")

    if active_deck:
        tutor.set_deck(active_deck)
    else:
        decks = tutor.deck_manager.list_decks()
        if decks:
            tutor.set_deck(decks[0])
            logger.info(f"Auto-loaded deck: {decks[0]}")
        else:
            logger.warning("No decks found. AI advice will lack deck context.")

    tutor.start(app)

    app.aboutToQuit.connect(tutor.stop)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
